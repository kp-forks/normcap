"""Main entry point for NormCap's UI.

This module hosts most the UI logic. The tray persists from NormCap's start until
the application is closed. Potential windows or other components are started from
here.
"""

import logging
import os
import sys
import time
from enum import Enum
from typing import Any, NoReturn, Optional, cast

from PySide6 import QtCore, QtGui, QtNetwork, QtWidgets

from normcap import __version__, clipboard, notification, screenshot
from normcap.detection import detector, ocr
from normcap.detection.models import DetectionMode, TextDetector, TextType
from normcap.gui import (
    constants,
    introduction,
    notification_utils,
    permissions_dialog,
    resources,  # noqa: F401 (loads resources!)
    system_info,
    utils,
)
from normcap.gui.language_manager import LanguageManager
from normcap.gui.localization import _
from normcap.gui.menu_button import MenuButton
from normcap.gui.models import Days, Rect, Screen, Seconds
from normcap.gui.settings import Settings
from normcap.gui.update_check import UpdateChecker
from normcap.gui.window import Window

logger = logging.getLogger(__name__)


class TrayIcon(Enum):
    NORMAL = ":tray"
    DONE = ":tray_done"


class Communicate(QtCore.QObject):
    """TrayMenus' communication bus."""

    exit_application = QtCore.Signal(float)
    on_copied_to_clipboard = QtCore.Signal()
    on_region_selected = QtCore.Signal(Rect, int)
    on_languages_changed = QtCore.Signal(list)


class SystemTray(QtWidgets.QSystemTrayIcon):
    """System tray icon with menu."""

    _EXIT_DELAY: Seconds = 5
    _UPDATE_CHECK_INTERVAL: Days = 7

    # Only for testing purposes: forcefully enables language manager in settings menu
    # (Normally language manager is only available in pre-build version)
    _testing_language_manager = False

    # Used for singleton:
    _socket_name = f"v{__version__}-normcap"
    _socket_out: Optional[QtNetwork.QLocalSocket] = None
    _socket_in: Optional[QtNetwork.QLocalSocket] = None
    _socket_server: Optional[QtNetwork.QLocalServer] = None

    def __init__(self, parent: QtCore.QObject, args: dict[str, Any]) -> None:
        logger.debug("System info:\n%s", system_info.to_dict())
        super().__init__(parent)

        # Prepare and connect signals
        self.com = Communicate(parent=self)
        self._set_signals()

        # Prepare instance attributes
        self.windows: dict[int, Window] = {}
        self.screens: list[Screen] = system_info.screens()
        self.installed_languages: list[str] = []
        self.settings = Settings(init_settings=args)

        self.screenshot_handler_name = args.get("screenshot_handler")
        self.clipboard_handler_name = args.get("clipboard_handler")
        self.notification_handler_name = args.get("notification_handler")

        # Handle special cli args
        if args.get("reset", False):
            self.settings.reset()
        self.cli_mode = args.get("cli_mode", False)

        # Setup timers
        # TODO: Handle timers less verbose and init in separate method
        self.reset_tray_icon_timer = QtCore.QTimer(parent=self)
        self.reset_tray_icon_timer.setSingleShot(True)
        self.reset_tray_icon_timer.timeout.connect(self._set_tray_icon_normal)

        self.delayed_exit_timer = QtCore.QTimer(parent=self)
        self.delayed_exit_timer.setSingleShot(True)
        self.delayed_exit_timer.timeout.connect(self.hide)

        self.delayed_init_timer = QtCore.QTimer(parent=self)
        self.delayed_init_timer.setSingleShot(True)
        self.delayed_init_timer.timeout.connect(self._delayed_init)
        self.delayed_init_timer.start(50)

        # Check/get prerequisites for running
        if not self._ensure_single_instance():
            self.com.exit_application.emit(0)
            return

        # Prepare UI
        self._set_tray_icon_normal()

        self.tray_menu = QtWidgets.QMenu(None)
        self.tray_menu.aboutToShow.connect(self._populate_context_menu_entries)

        self.setContextMenu(self.tray_menu)
        self._populate_context_menu_entries()

        # Verify screenshot permissions
        if not self.settings.value("has-screenshot-permission", type=bool):
            if screenshot.has_screenshot_permission():
                self.settings.setValue("has-screenshot-permission", True)
            else:
                self.show_permissions_info()

        # Show intro (and delay screenshot to not capute the intro)
        if (
            args.get("show_introduction") is None
            and self.settings.value("show-introduction", type=bool)
        ) or args.get("show_introduction") is True:
            self.show_introduction()
            delay_screenshot = True
        else:
            delay_screenshot = False

        if not args.get("background_mode", False):
            self._show_windows(delay_screenshot=delay_screenshot)

    @QtCore.Slot()
    def show_introduction(self) -> None:
        show_intro = bool(self.settings.value("show-introduction", type=bool))
        result = introduction.IntroductionDialog(
            show_on_startup=show_intro,
            parent=self.windows[0] if self.windows else None,
        ).exec()
        if result == introduction.Choice.SHOW:
            self.settings.setValue("show-introduction", True)
        if result == introduction.Choice.DONT_SHOW:
            self.settings.setValue("show-introduction", False)

    @QtCore.Slot()
    def show_permissions_info(self) -> None:
        logger.error("Missing screenshot permission!")
        delay = 0

        if sys.platform == "darwin":
            calling_app = "NormCap" if system_info.is_prebuilt_package() else "Terminal"
            text = constants.PERMISSIONS_TEXT_MACOS.format(application=calling_app)

            # Reset privacy permission in case of new NormCap version. This is necessary
            # because somehow the setting is associated with the binary and won't work
            # after it got updated.
            screenshot.macos_reset_screenshot_permission()

        elif system_info.is_flatpak_package():
            text = constants.PERMISSIONS_TEXT_FLATPAK

        elif system_info.display_manager_is_wayland():
            text = constants.PERMISSIONS_TEXT_WAYLAND

        permissions_dialog.PermissionDialog(text=text).exec()
        self.com.exit_application.emit(delay)

    @QtCore.Slot()
    def _set_tray_icon_done(self) -> None:
        self.setIcon(QtGui.QIcon(TrayIcon.DONE.value))
        self.reset_tray_icon_timer.start(5000)

    @QtCore.Slot()
    def _on_new_connection(self) -> None:
        """Open incoming socket to listen for messages from other NormCap instances."""
        if not self._socket_server:
            return
        self._socket_in = self._socket_server.nextPendingConnection()
        if self._socket_in:
            logger.debug("Connect to incoming socket.")
            self._socket_in.readyRead.connect(self._on_ready_read)

    @QtCore.Slot()
    def _on_ready_read(self) -> None:
        """Process messages received from other NormCap instances."""
        if not self._socket_in:
            return

        message = self._socket_in.readAll().data().decode("utf-8", errors="ignore")
        if message != "capture":
            return

        logger.info("Received socket signal to capture.")
        if self.windows:
            logger.debug("Capture window(s) already open. Doing nothing.")
            return

        self._show_windows(delay_screenshot=True)

    @QtCore.Slot(QtWidgets.QSystemTrayIcon.ActivationReason)
    def _handle_tray_click(
        self, reason: QtWidgets.QSystemTrayIcon.ActivationReason
    ) -> None:
        logger.debug("Tray event: %s", reason)
        if (
            reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger
            and self.settings.value("tray", False, type=bool)
        ):
            self._show_windows(delay_screenshot=True)

    def _show_windows(self, delay_screenshot: bool) -> None:
        """Initialize child windows with method depending on system."""
        screenshots = self._take_screenshots(delay=delay_screenshot)

        for idx, image in enumerate(screenshots):
            self.screens[idx].screenshot = image

        for index in range(len(system_info.screens())):
            self._create_window(index)

    @QtCore.Slot(str)
    def _apply_setting_change(self, setting: str) -> None:
        if setting == "tray":
            capture_action = self.contextMenu().findChild(QtGui.QAction, name="capture")
            capture_action = cast(QtGui.QAction, capture_action)
            is_tray_visible = bool(self.settings.value(setting, False, type=bool))
            capture_action.setVisible(is_tray_visible)

    @QtCore.Slot(list)
    def _sanitize_language_setting(self, installed_languages: list[str]) -> None:
        """Verify that languages selected in the settings exist.

        If one doesn't, remove it. If none does, select the first in list.
        """
        active_languages = self.settings.value("language")
        if not isinstance(active_languages, list):
            active_languages = [active_languages]

        active_languages = [
            a for a in active_languages if a in installed_languages
        ] or [installed_languages[0]]

        self.settings.setValue("language", active_languages)

    @QtCore.Slot(list)
    def _update_installed_languages(self, installed_languages: list[str]) -> None:
        """Update instance attribute to reflect changes.

        the instance attribute is used e.g. to create a menu_button with an up to
        date language menu.
        """
        self.installed_languages = installed_languages

    @QtCore.Slot()
    def _trigger_detect(self, rect: Rect, screen_idx: int) -> None:
        """Crop screenshot, perform content recognition on it and process result."""
        cropped_screenshot = utils.crop_image(
            image=self.screens[screen_idx].screenshot, rect=rect
        )

        minimum_image_area = 100
        image_area = cropped_screenshot.width() * cropped_screenshot.height()
        if image_area < minimum_image_area:
            logger.warning("Area of %spx is too small. Skip detection.", image_area)
            self._minimize_or_exit_application(delay=0)
            return

        tessdata_path = system_info.get_tessdata_path(
            config_directory=system_info.config_directory(),
            is_flatpak_package=system_info.is_flatpak_package(),
            is_briefcase_package=system_info.is_briefcase_package(),
        )
        tesseract_bin_path = system_info.get_tesseract_bin_path(
            is_briefcase_package=system_info.is_briefcase_package()
        )

        detection_mode = DetectionMode(0)
        if bool(self.settings.value("detect-codes", type=bool)):
            detection_mode |= DetectionMode.CODES
        if bool(self.settings.value("detect-text", type=bool)):
            detection_mode |= DetectionMode.TESSERACT

        result = detector.detect(
            image=cropped_screenshot,
            tesseract_bin_path=tesseract_bin_path,
            tessdata_path=tessdata_path,
            language=self.settings.value("language"),
            detect_mode=detection_mode,
            parse_text=bool(self.settings.value("parse-text", type=bool)),
        )

        if result.text and self.cli_mode:
            self._print_to_stdout_and_exit(text=result.text)
        elif result.text:
            self._copy_to_clipboard(
                text=result.text, result_type=result.text_type, detector=result.detector
            )
        else:
            logger.warning("Nothing detected on selected region.")

        if self.settings.value("notification", type=bool):
            self._send_notification(
                text=result.text, text_type=result.text_type, detector=result.detector
            )

        self._minimize_or_exit_application(delay=self._EXIT_DELAY)
        self._set_tray_icon_done()

    def _send_notification(
        self, text: str, text_type: TextType, detector: TextDetector
    ) -> None:
        title, message = notification_utils._compose_notification(
            text=text, result_type=text_type, detector=detector
        )
        action_label = notification_utils._get_action_label(text_type=text_type)

        # TODO: refactor to use one function with optional handler_name
        if self.notification_handler_name:
            notification.notify_with_handler(
                handler_name=self.notification_handler_name,
                title=title,
                message=message,
                action_label=action_label,
                action_callback=lambda: notification_utils._open_ocr_result(
                    text=text, text_type=text_type
                ),
            )

        else:
            notification.notify(
                title=title,
                message=message,
                action_label=action_label,
                action_callback=lambda: notification_utils._open_ocr_result(
                    text=text, text_type=text_type
                ),
            )

    @QtCore.Slot(str)
    def _open_url_and_hide(self, url: str) -> None:
        """Open url in default browser, then hide to tray or exit."""
        logger.debug("Open %s", url)
        result = QtGui.QDesktopServices.openUrl(
            QtCore.QUrl(url, QtCore.QUrl.ParsingMode.TolerantMode)
        )
        logger.debug("Opened uri with result=%s", result)
        self._minimize_or_exit_application(delay=0)

    @QtCore.Slot()
    def _open_language_manager(self) -> None:
        """Open url in default browser, then hide to tray or exit."""
        logger.debug("Loading language manager …")
        self.language_window = LanguageManager(
            tessdata_path=system_info.config_directory() / "tessdata",
            parent=self.windows[0],
        )
        self.language_window.com.on_open_url.connect(self._open_url_and_hide)
        self.language_window.com.on_languages_changed.connect(
            self.com.on_languages_changed
        )
        self.language_window.exec()

    @QtCore.Slot(str, str, str)
    def _copy_to_clipboard(self, text: str, result_type: str, detector: str) -> None:
        """Copy results to clipboard."""
        if self.clipboard_handler_name:
            logger.debug(
                "Copy text to clipboard with %s", self.clipboard_handler_name.upper()
            )
            clipboard.copy_with_handler(
                text=text, handler_name=self.clipboard_handler_name
            )
        else:
            logger.debug("Copy text to clipboard")
            clipboard.copy(text=text)
        self.com.on_copied_to_clipboard.emit()

    @QtCore.Slot(str)
    def _print_to_stdout_and_exit(self, text: str) -> None:
        """Print results to stdout ."""
        logger.debug("Print text to stdout and exit.")
        print(text, file=sys.stdout)  # noqa: T201
        self.com.exit_application.emit(0)

    @QtCore.Slot()
    def _close_windows(self) -> None:
        """Hide all windows of normcap."""
        window_count = len(self.windows)
        if window_count < 1:
            return
        logger.debug("Hide %s window%s", window_count, "s" if window_count > 1 else "")
        QtWidgets.QApplication.restoreOverrideCursor()
        QtWidgets.QApplication.processEvents()
        for window in self.windows.values():
            window.close()
        self.windows = {}

    def _delayed_init(self) -> None:
        """Setup things that can be done independent of the first capture.

        By running this async of __init__(),  its runtime of ~30ms doesn't
        contribute to the delay until the GUI becomes active for the user on startup.
        """
        self.installed_languages = ocr.tesseract.get_languages(
            tesseract_cmd=system_info.get_tesseract_bin_path(
                is_briefcase_package=system_info.is_briefcase_package()
            ),
            tessdata_path=system_info.get_tessdata_path(
                config_directory=system_info.config_directory(),
                is_briefcase_package=system_info.is_briefcase_package(),
                is_flatpak_package=system_info.is_flatpak_package(),
            ),
        )
        self.com.on_languages_changed.emit(self.installed_languages)
        self._add_update_checker()

    def _set_tray_icon_normal(self) -> None:
        self.setIcon(QtGui.QIcon(TrayIcon.NORMAL.value))

    def _create_socket_server(self) -> None:
        """Open socket server to listen for other NormCap instances."""
        if self._socket_out:
            self._socket_out.close()
            self._socket_out = None
        QtNetwork.QLocalServer().removeServer(self._socket_name)
        self._socket_server = QtNetwork.QLocalServer(self)
        self._socket_server.newConnection.connect(self._on_new_connection)
        self._socket_server.listen(self._socket_name)
        logger.debug("Listen on local socket %s.", self._socket_server.serverName())

    def _ensure_single_instance(self) -> bool:
        self._socket_out = QtNetwork.QLocalSocket(self)
        self._socket_out.connectToServer(self._socket_name)
        if self._socket_out.waitForConnected():
            logger.debug("Another instance is already running. Sending capture signal.")
            self._socket_out.write(b"capture")
            self._socket_out.waitForBytesWritten(1000)
            return False

        self._create_socket_server()
        return True

    def _set_signals(self) -> None:
        """Set up signals to trigger program logic."""
        self.activated.connect(self._handle_tray_click)
        self.com.on_region_selected.connect(self._close_windows)
        self.com.on_region_selected.connect(self._trigger_detect)
        self.com.on_languages_changed.connect(self._sanitize_language_setting)
        self.com.on_languages_changed.connect(self._update_installed_languages)
        self.com.exit_application.connect(self._exit_application)
        self.messageClicked.connect(self._open_language_manager)

    def _add_update_checker(self) -> None:
        if not self.settings.value("update", type=bool):
            return

        now_sub_interval_sec = time.time() - (
            60 * 60 * 24 * self._UPDATE_CHECK_INTERVAL
        )
        now_sub_interval = time.strftime("%Y-%m-%d", time.gmtime(now_sub_interval_sec))
        if str(self.settings.value("last-update-check", type=str)) > now_sub_interval:
            return

        self.checker = UpdateChecker(
            parent=None, packaged=system_info.is_prebuilt_package()
        )
        self.checker.com.on_version_checked.connect(
            self._update_time_of_last_update_check
        )
        self.checker.com.on_click_get_new_version.connect(self._open_url_and_hide)
        QtCore.QTimer.singleShot(500, self.checker.com.check.emit)

    def _update_time_of_last_update_check(self, newest_version: str) -> None:
        if newest_version is not None:
            today = time.strftime("%Y-%m-%d", time.gmtime())
            self.settings.setValue("last-update-check", today)

    @QtCore.Slot()
    def _take_screenshots(self, delay: bool) -> list[QtGui.QImage]:
        """Get new screenshots and cache them."""
        if delay:
            # Timeout should be high enough for visible windows to completely hide and
            # short enough to not annoy the users to much. (FTR: 0.15 was too short.)
            time.sleep(0.5)

        if self.screenshot_handler_name:
            logger.debug(
                "Take screenshot explicitly with %s",
                self.screenshot_handler_name.upper(),
            )
            screens = screenshot.capture_with_handler(
                handler_name=self.screenshot_handler_name
            )
        else:
            screens = screenshot.capture()

        if not screens:
            raise RuntimeError("No screenshot taken!")

        for idx, image in enumerate(screens):
            utils.save_image_in_temp_folder(image, postfix=f"_raw_screen{idx}")

        return screens

    @QtCore.Slot()
    def _populate_context_menu_entries(self) -> None:
        """Create menu for system tray."""
        self.tray_menu.clear()

        # L10N: Tray menu entry
        action = QtGui.QAction(_("Capture"), self.tray_menu)
        action.setObjectName("capture")
        action.triggered.connect(lambda: self._show_windows(delay_screenshot=True))
        action.setVisible(bool(self.settings.value("tray", False, type=bool)))
        self.tray_menu.addAction(action)

        # L10N: Tray menu entry for exiting NormCap completely.
        action = QtGui.QAction(_("Exit"), self.tray_menu)
        action.setObjectName("exit")
        action.triggered.connect(lambda: self.com.exit_application.emit(0))
        self.tray_menu.addAction(action)

    def _create_window(self, index: int) -> None:
        """Open a child window for the specified screen."""
        new_window = Window(
            screen=self.screens[index], settings=self.settings, parent=None
        )
        new_window.com.on_esc_key_pressed.connect(
            lambda: self._minimize_or_exit_application(delay=0)
        )
        new_window.com.on_esc_key_pressed.connect(
            lambda: self._minimize_or_exit_application(delay=0)
        )
        new_window.com.on_region_selected.connect(self.com.on_region_selected)
        if index == 0:
            menu_button = self._create_menu_button()
            layout = self._create_layout()
            layout.addWidget(menu_button, 0, 1)
            new_window.ui_container.setLayout(layout)

        new_window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        new_window.set_fullscreen()
        self.windows[index] = new_window

    def _create_menu_button(self) -> QtWidgets.QWidget:
        if self._testing_language_manager:
            system_info.is_briefcase_package = lambda: True
        settings_menu = MenuButton(
            settings=self.settings,
            language_manager=system_info.is_prebuilt_package(),
            installed_languages=self.installed_languages,
        )
        settings_menu.com.on_open_url.connect(self._open_url_and_hide)
        settings_menu.com.on_manage_languages.connect(self._open_language_manager)
        settings_menu.com.on_setting_change.connect(self._apply_setting_change)
        settings_menu.com.on_show_introduction.connect(self.show_introduction)
        settings_menu.com.on_close_in_settings.connect(
            lambda: self._minimize_or_exit_application(delay=0)
        )
        self.com.on_languages_changed.connect(settings_menu.on_languages_changed)
        return settings_menu

    @staticmethod
    def _create_layout() -> QtWidgets.QGridLayout:
        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(26, 26, 26, 26)
        layout.setRowStretch(1, 1)
        layout.setColumnStretch(0, 1)
        return layout

    @QtCore.Slot()
    def _minimize_or_exit_application(self, delay: Seconds) -> None:
        self._close_windows()
        if self.settings.value("tray", type=bool):
            return

        self.com.exit_application.emit(delay)

    @QtCore.Slot(bool)
    def _exit_application(self, delay: Seconds) -> None:
        # Unregister the singleton server
        if self._socket_server:
            self._socket_server.close()
            self._socket_server.removeServer(self._socket_name)
            self._socket_server = None

        if delay:
            self.delayed_exit_timer.start(int(delay * 1000))
        else:
            self.hide()

    def hide(self) -> NoReturn:
        """Perform last cleanups before quitting application.

        Note: Don't call directly! Instead do `self.com.exit_application.emit(0)`!
        """
        # First call QSystemTrayIcon's method
        super().hide()

        # Leave some time to process final events
        QtWidgets.QApplication.processEvents()
        time.sleep(0.05)

        # Final log messages
        logger.info("Exit normcap")
        logger.debug(
            "Debug images saved in %s%snormcap", utils.tempfile.gettempdir(), os.sep
        )

        # The preferable QApplication.quit() doesn't work reliably on macOS. E.g. when
        # right clicking on "close" in tray menu, NormCap process keeps running.
        sys.exit(0)

"""Run adjustments while packaging with briefcase during CI/CD."""

import shutil
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from retry import retry

from platforms.utils import BuilderBase, bundle_tesseract_windows_ub_mannheim


class WindowsBriefcase(BuilderBase):
    """Create prebuilt package for Windows using Briefcase."""

    binary_suffix = ""
    binary_extension = "msi"
    binary_platform = "x86_64-Windows"

    @retry(tries=5, delay=1, backoff=2)
    def _download_openssl(self) -> None:
        """Download openssl needed for QNetwork https connections."""
        # For mirrors see: https://wiki.openssl.org/index.php/Binaries
        # openssl_url = "http://mirror.firedaemon.com/OpenSSL/openssl-1.1.1q.zip"
        # openssl_url = "http://wiki.overbyte.eu/arch/openssl-1.1.1q-win64.zip"
        openssl_url = "https://indy.fulgan.com/SSL/openssl-1.0.2u-x64_86-win64.zip"
        target_path = self.PROJECT_PATH / "normcap" / "resources" / "openssl"
        target_path.mkdir(exist_ok=True)
        zip_path = self.BUILD_PATH / "openssl.zip"
        urllib.request.urlretrieve(openssl_url, zip_path)  # noqa: S310
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(target_path)

        zip_path.unlink()

    def _patch_windows_installer(self) -> None:
        """Customize wix-installer."""
        wxs_file = (
            self.PROJECT_PATH
            / "build"
            / "normcap"
            / "windows"
            / "visualstudio"
            / "normcap.wxs"
        )

        # Cache header for inserting later
        with Path(wxs_file).open(encoding="utf-8") as f:
            header_lines = f.readlines()[:3]

        ns = "{http://schemas.microsoft.com/wix/2006/wi}"
        ET.register_namespace("", ns[1:-1])

        tree = ET.parse(wxs_file)  # noqa: S314
        root = tree.getroot()
        product = root.find(f"{ns}Product")
        if not product:
            raise ValueError("Product section not found!")

        # Copy installer images
        left = "normcap_install_bg.bmp"
        top = "normcap_install_top.bmp"

        for image in (left, top):
            original = self.IMG_PATH / image
            target = (
                self.PROJECT_PATH
                / "build"
                / "normcap"
                / "windows"
                / "visualstudio"
                / image
            )
            shutil.copy(original, target)

        # Set installer images
        ET.SubElement(
            product, "WixVariable", {"Id": "WixUIDialogBmp", "Value": f"{left}"}
        )
        ET.SubElement(
            product, "WixVariable", {"Id": "WixUIBannerBmp", "Value": f"{top}"}
        )

        # Allow upgrades
        major_upgrade = ET.SubElement(product, "MajorUpgrade")
        major_upgrade.set("Schedule", "afterInstallInitialize")
        major_upgrade.set("DowngradeErrorMessage", "Can't downgrade. Uninstall first.")

        # Cleanup tessdata folder on uninstall
        ET.SubElement(
            product,
            "CustomAction",
            {
                "Id": "Cleanup_orphaned_files",
                "Directory": "TARGETDIR",
                "ExeCommand": (
                    'cmd /C "rmdir /s /q %localappdata%\\normcap '
                    '& rmdir /s /q %localappdata%\\dynobo";'
                ),
                "Execute": "deferred",
                "Return": "ignore",
                "HideTarget": "no",
                "Impersonate": "no",
            },
        )
        sequence = product.find(f"{ns}InstallExecuteSequence")
        if not sequence:
            raise ValueError("InstallExecuteSequence section not found!")
        ET.SubElement(
            sequence,
            "Custom",
            {"Action": "Cleanup_orphaned_files", "Before": "RemoveFiles"},
        ).text = '(REMOVE = "ALL") AND NOT UPGRADINGPRODUCTCODE'

        # Remove node which throws error during compilation
        remove_existing_product = sequence.find(f"{ns}RemoveExistingProducts")
        sequence.remove(remove_existing_product)  # type: ignore

        upgrade = product.find(f"{ns}Upgrade")
        if not upgrade:
            raise ValueError("Upgrade section not found!")
        product.remove(upgrade)

        # Write & fix header
        tree.write(wxs_file, encoding="utf-8", xml_declaration=False)
        with Path(wxs_file).open("r+", encoding="utf-8") as f:
            lines = f.readlines()
            f.seek(0)
            f.writelines(header_lines + lines)

    def bundle_tesseract(self) -> None:
        """Download tesseract binaries including dependencies into resource path."""
        bundle_tesseract_windows_ub_mannheim(self)

    def run_framework(self) -> None:
        self.run(cmd="briefcase create windows VisualStudio", cwd=self.PROJECT_PATH)
        self.run(cmd="briefcase build windows VisualStudio", cwd=self.PROJECT_PATH)
        self._patch_windows_installer()
        self.run(cmd="briefcase package windows VisualStudio", cwd=self.PROJECT_PATH)

    def install_system_deps(self) -> None: ...

    def pre_framework(self) -> None:
        self.bundle_tesseract()
        self._download_openssl()

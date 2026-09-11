#!/usr/bin/env python3

import argparse
import getpass
import hashlib
import os
import random
import shutil
import string
import subprocess
import sys
import urllib.request
from pathlib import Path


def get_system_locale():
    locale = os.environ.get("LANG", "en_US.UTF-8")
    return locale.split(".")[0]


def get_system_timezone():
    if os.path.exists("/etc/timezone"):
        with open("/etc/timezone", "r") as f:
            return f.read().strip()
    if os.path.exists("/etc/localtime"):
        return str(Path("/etc/localtime").resolve()).split("/zoneinfo/")[-1]
    return "UTC"


INSTALLER_IMAGE_URL = "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-13.6.0-amd64-netinst.iso"
INSTALLER_IMAGE_SHA256_SUM = "65273beed27b2df543b68b65630ba525cfbad8df2b12035732b2dff87d6664e7"

DEFAULT_LOCALE = get_system_locale()
DEFAULT_TIMEZONE = get_system_timezone()


def get_default_cpus():
    try:
        return os.cpu_count() // 2
    except:
        return 2


def download_file(url, dest_path):
    print(f"Downloading {url} to {dest_path}...")
    with urllib.request.urlopen(url) as response, open(dest_path, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)


def verify_hash(file_path, expected_hash):
    print(f"Verifying hash for {file_path}...")
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    actual_hash = sha256_hash.hexdigest()
    if actual_hash != expected_hash:
        print(f"Hash mismatch! Expected: {expected_hash}, Actual: {actual_hash}")
        sys.exit(1)
    print("Hash verified successfully.")


def get_password_hash(password):
    # Using openssl to generate a crypt-compatible hash for the preseed
    # d-i passwd/root-password-crypted password Expects a crypt(3) hash.
    # We'll use SHA-512 ($6$)
    cmd = ["openssl", "passwd", "-6", password]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def parse_arguments():
    parser = argparse.ArgumentParser(description="Create a Debian VM using virt-install")
    parser.add_argument("--installer-image",
                        default=INSTALLER_IMAGE_URL,
                        help="URL of the Debian installer ISO")
    parser.add_argument("--installer-image-sha256sum",
                        default=INSTALLER_IMAGE_SHA256_SUM,
                        help="Expected SHA256 hash of the installer ISO")
    parser.add_argument("--cpu", type=int, default=get_default_cpus(),
                        help="Number of CPUs for the VM")
    parser.add_argument("--ram", default="8192",
                        help="RAM in MB (default 8GB/8192MB)")
    parser.add_argument("--name", default="attack-box",
                        help="Name of the VM")
    parser.add_argument("--locale", default=DEFAULT_LOCALE,
                        help=f"Locale for the VM (default: {DEFAULT_LOCALE})")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE,
                        help=f"Timezone for the VM (default: {DEFAULT_TIMEZONE})")
    parser.add_argument('--set-root-password', action='store_true',
                        help='Prompt for root password. If not set, a random password will be generated.')

    return parser.parse_args()


def get_root_password():
    while True:
        root_password = getpass.getpass("Enter root password: ")
        root_password_confirm = getpass.getpass("Confirm root password: ")
        if root_password == root_password_confirm:
            return root_password
        print("Passwords do not match. Please try again.")


def get_random_password():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(20))


def prepare_installer_image(image_url, expected_hash):
    downloads_dir = Path.home() / "Downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    iso_name = image_url.split("/")[-1]
    iso_path = downloads_dir / iso_name

    if not iso_path.exists():
        download_file(image_url, iso_path)
    else:
        print(f"ISO already exists at {iso_path}")

    if expected_hash:
        verify_hash(iso_path, expected_hash)

    return iso_path


def generate_preseed(root_password, locale, timezone, hostname):
    template_path = Path(__file__).parent.parent / "preseed" / "preseed.template.cfg"
    if not template_path.exists():
        print(f"Template not found at {template_path}")
        sys.exit(1)

    root_password_hash = get_password_hash(root_password)

    with open(template_path, 'r') as f:
        template_content = f.read()

    preseed_content = template_content.format(
        root_password_hash=root_password_hash,
        locale=locale,
        timezone=timezone,
        hostname=hostname,
    )

    preseed_path = Path(__file__).parent.parent / "preseed" / "preseed.cfg"
    with open(preseed_path, 'w') as f:
        f.write(preseed_content)

    print(f"Generated preseed.cfg at {preseed_path}")
    return preseed_path


def run_virt_install(connection, name, cpu, ram, iso_path, preseed_path, config_path, tools_path, transfer_path):
    cmd = [
        "virt-install",
        "--connect", connection,
        "--name", name,
        "--vcpus", str(cpu),
        "--memory", ram,
        "--location", f"{iso_path},kernel=install.amd/vmlinuz,initrd=install.amd/initrd.gz",
        "--disk", "size=40,format=qcow2",
        "--os-variant", "debian13",
        "--initrd-inject", str(preseed_path),
        "--initrd-inject", str(Path(__file__).parent.parent / "preseed" / "bootstrap"),
        "--extra-args", "auto=true priority=critical",
        "--filesystem", f"{config_path},configuration,mode=mapped,readonly=yes",
        "--filesystem", f"{tools_path},tools,mode=mapped,readonly=yes",
        "--filesystem", f"{transfer_path},transfer,mode=mapped",
        # "--network", "network=default",
        "--network", "passt",
        '--video', 'qxl',
        '--channel', 'spicevmc,target.type=virtio',  # needed for spice-vdagent
        '--channel', 'unix,mode=bind,target_type=virtio,name=org.qemu.guest_agent.0',  # needed for qemu-guest-agent
        "--noautoconsole"
    ]

    print(f"Running command: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True)
        print("VM creation initiated successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error creating VM: {e}")
        sys.exit(1)




def main():
    args = parse_arguments()
    if args.set_root_password:
        root_password = get_root_password()
    else:
        root_password = get_random_password()
        print(f'Generated random root password: {root_password}')
    iso_path = prepare_installer_image(args.installer_image, args.installer_image_sha256sum)
    preseed_path = generate_preseed(
        root_password=root_password,
        locale=args.locale,
        timezone=args.timezone,
        hostname=args.name,
    )

    project_root = Path(__file__).parent.parent.absolute()
    config_path = project_root / "configuration"
    tools_path = project_root / "tools"
    transfer_path = project_root / "transfer"

    connection = "qemu:///session"
    run_virt_install(connection, args.name, args.cpu, args.ram, iso_path, preseed_path, config_path, tools_path,
                     transfer_path)

    print('\nAfter the VM has shut down, start it again. '
          'It will the run the initial configuration and shut down a second time. '
          'After that, the setup is complete.')


if __name__ == "__main__":
    main()

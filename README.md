# attack-box

Automatic installer of Debian 13 / ParrotOS based machine to use for CTF challenges, customised to be convenient
for me (... probably only me).

The idea is to create throwaway boxes (VMs), as isolated as reasonable while still convenient, with all personal
tooling, customisations, and configuration stored outside under version control.

## Features

* qemu/kvm VM via userspace libvirt
* installer wrapping virt-install & Debian preseed
* ansible for applying configuration and installing software
* i3
    * shortcuts for workspace management removed intentionally to not confuse them with the host
    * daemon to automatically adapt guest screen resolution
* liquidprompt
* remove some of the ParrotOS customisations
* pre-configured mount points to mount volumes into the box
    * configuration (read-only) containing the ansible configuration
    * tools (read-only) containing custom scripts
    * transfer (read/write, no automount) to move files in and out

## Usage

### Create VM
Run 
```
./scripts/create-vm.sh
```
and follow the instructions, or see
```
./script/create-vm.sh --help
```
for more information. If you observe errors, you probably need to install missing dependencies for your libvirt setup.

Once the installations is complete, start the VM with
```
virsh start --domain attack-box
```
and connect to the console, e.g. with one of the following tools:
```
virt-manager --connect qemu:///session --show-domain-console attack-box
virt-viewer attack-box
remmina -c spice://127.0.0.1:5900
```

### Useful commands within VM

Start i3
```
startx
```

Mount / unmount writable transfer dir (not auto-mounted)
```
mount /mnt/transfer
umount /mnt/transfer
```

Apply configuration via ansible
```
/mnt/configuration/apply
```

## Adopt

Feel free to fork and adapt to your needs.

* you probably want to adapt at least the [keyboard layout](configuration/roles/common/vars/main.yml)

## License

[The Unlicense](http://unlicense.org/)

Obviously, that license refers only to the scripts and configuration in this repository.
Software installed in the VM, especially Debian & ParrotOS, have their own licenses.

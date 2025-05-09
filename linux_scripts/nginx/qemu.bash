qemu-system-x86_64 \
  -m 64M \
  -smp cpus=1,threads=1,sockets=1 \
  -cpu host,+x2apic,-pmu \
  -netdev user,id=net0,hostfwd=tcp::8080-:80 \
  -device virtio-net-pci,netdev=net0 \
  -drive file=ubuntu.qcow2,format=qcow2 \
  -cdrom seed.iso \
  -enable-kvm \
  -nographic \
  -serial mon:stdio



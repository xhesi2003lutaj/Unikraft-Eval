sudo /usr/bin/qemu-system-x86_64 \
    -fsdev local,id=myid,path=$(pwd)/fs0,security_model=none \
    -device virtio-9p-pci,fsdev=myid,mount_tag=fs0,disable-modern=on,disable-legacy=off \
    -netdev user,id=coolen0,hostfwd=tcp::8080-:80 \
    -device virtio-net-pci,netdev=coolen0 \
    -append "netdev.ipv4_addr=172.44.0.2 netdev.ipv4_gw_addr=172.44.0.1 netdev.ipv4_subnet_mask=255.255.255.0 --" \
    -kernel build/nginx_qemu-x86_64 \
    -nographic

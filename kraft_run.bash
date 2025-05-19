# Manual creation of the image
# kraft build ~= qemu with application apecific command arguments
	# builds the filesystem specific to the appliation through a Dockerfile
	# configures the kernel through the specifications on the Kraftfile
		# pulls the required libraries/repositories
		# configures these libraries
	# complies the repostories 
	# result: a kernel image that embeds the filesystem
# kraft run
	# start qemu with the kernel image generated above and the command from the Kraftfile : cmd:['/usr'] 


kraft build --plat qemu --arch x86_64 .
kraft run port --plat qemu --arch x86_64.
kraft run --log-level debug --log-type basic -p port ...


# kraft run -p  --plat  --arch //using the pulled image  
# pulls the base runtime
# builds the application filesystem using a Dockerfile
	# pulls the Docker library image 
	# copies the required files in the Docker filesystem
	# builds the required files into the output executable (/server)
# runs the application on top of Unikraft 	


kraft run --plat --arch #= (example for nginx)
            sudo qemu-system-x86_64 \
            -kernel .unikraft/build/nginx_qemu-x86_64 \
            -append "netdev.ipv4_addr=172.44.0.2 netdev.ipv4_gw_addr=172.44.0.1 netdev.ipv4_subnet_mask=255.255.255.0 --" \
            -fsdev local,id=myid,path=$(pwd)/rootfs/nginx,security_model=none \
            -device virtio-9p-pci,fsdev=myid,mount_tag=nginx,disable-modern=on,disable-legacy=off \
            -netdev user,id=net0,hostfwd=tcp::8080-:80 \
            -device virtio-net-pci,netdev=net0 \
            -m 64M \
            -nographic



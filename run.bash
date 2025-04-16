# Manual creation of the image
# kraft build ~= qemu with application apecific command arguments
# builds the filesystem specific to the appliation through a Dockerfile
# configures the kernel through the specifications on the Kraftfile
	# pulls the required libraries/repositories
	# configures these libraries
# complies the repostories 
# result: a kernel image that embeds the filesystem

kraft build --plat qemu --arch x86_64 .
kraft run port --plat qemu --arch x86_64


# kraft run -p  --plat  --arch //using the pulled image  
# pulls the base runtime
# builds the application filesystem sing a Dockerfile
	# pulls the Docker library image 
	# copies the required files in the Docker filesystem
	# builds the required files into the output executable (/server)
# runs the application on top of Unikraft 	



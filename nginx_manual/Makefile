UK_ROOT ?= $(PWD)/.unikraft/unikraft
UK_LIBS ?= $(PWD)/.unikraft/libs
#UK_BUILD ?= $(PWD)/workdir/build
LIBS := $(UK_LIBS)/musl:$(UK_LIBS)/lwip:$(UK_LIBS)/nginx

all:
	@$(MAKE) -C $(UK_ROOT) A=$(PWD) L=$(LIBS) 

$(MAKECMDGOALS):
	@$(MAKE) -C $(UK_ROOT) A=$(PWD) L=$(LIBS)  $(MAKECMDGOALS)

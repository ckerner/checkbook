CURDIR=$(shell pwd)
LOCLDIR=/usr/local/bin

install: checkbook

update: checkbook

checkbook: .FORCE
	cp -fp $(CURDIR)/checkbook.py $(LOCLDIR)/checkbook.py

clean:
	rm -f $(LOCLDIR)/checkbook.py

.FORCE:



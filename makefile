VERS=pygossip-0.6
V=pygossip-0_6

tar:
	cvs export -r $(V) -d $(VERS) pygossip
	tar cvf $(VERS).tar $(VERS)
	gzip -v $(VERS).tar
	rm -rf $(VERS)

tag:
	cvs tag -F $(V)

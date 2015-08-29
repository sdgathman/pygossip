VERS=pygossip-0.7
V=pygossip-0_7

tar:
	cvs export -r $(V) -d $(VERS) pygossip
	tar cvf $(VERS).tar $(VERS)
	gzip -v $(VERS).tar
	rm -rf $(VERS)

tag:
	cvs tag -F $(V)

#! /usr/bin/env python
# Test program read_int.py

fin = open ('sh_sw_vlan')
fout = open ('sh_sw_vlan2', 'w')
for line in fin:
	print line
	fout.writelines(line)
fin.close()
fout.close()


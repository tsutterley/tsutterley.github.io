#!/usr/bin/env python
u"""
grace_months_html.py
Written by Tyler Sutterley (04/2016)

Creates a html file with the start and end days for each dataset
Shows the range of each month for (CSR/GFZ/JPL) (RL04/RL05)
Shows which months are missing for each dataset as **missing**

Similar to ftp://podaac.jpl.nasa.gov/allData/tellus/L3/Doc/GraceMonths.html
	ftp://podaac.jpl.nasa.gov/allData/tellus/L3/Doc/gracemonths_20160112.html

INPUTS:
	Date files from read_grace.py or grace_date.py (e.g. CSR_RL05_dates.txt)

OUTPUTS:
	GRACE_months.txt
	Column 1: Month Number e.g. 004
	Column 2: Month Name e.g. Apr
	Column 3: CSR RL04 Dates
	Column 4: GFZ RL04 Dates
	Column 5: JPL RL04 Dates
	Column 6: CSR RL05 Dates
	Column 7: GFZ RL05 Dates
	Column 8: JPL RL05 Dates

COMMAND LINE OPTIONS:
	--help: list the command line options
	--rl04: include release 4 datafiles

PYTHON DEPENDENCIES:
	numpy: Scientific Computing Tools For Python (http://www.numpy.org)

PROGRAM DEPENDENCIES:
	base_directory.py: sets the full path to the data directory
		PYTHONDATA environmental variable set in .pythonrc file
	date_string.py: finds the name of each month (e.g. Apr)

UPDATE HISTORY:
	Forked 04/2016: forked for HTML table creation
	Updated 03/2016: using getopt to set RL04 parameter, added new help module
		forked for markdown table creation
	Updated 10/2015: cleaned up and added a few comments
	Updated 11/2014: minor updates to code. added main definition
	Updated 10/2014: updated comments, current Sean Geocenter file
	Updated 05/2014: added OPTION to not run RL04
	Updated 07/2013: minor update: new Sean geocenter file
		moved geocenter files to grace.dir/geocenter.dir/
	Updated 05/2013: converted to Python and added years to month label
	Updated 03/2013: changed degree 1 to show both RL04 and RL05
	Updated 02/2013: new degree 1 file from Sean Swenson
		Changed to read from ascii files created from grace_date.pro
	Updated 11/2012: added DEG1 and SLR outputs
	Written 07/2012
"""
import sys
import os
import getopt
import inspect
import numpy as np
from datetime import date
from tyler_library.base_directory import base_directory
from tyler_library.date_string import date_string

def grace_months(RL04=False):

	#-- Directory Setup
	#-- base_dir is the full path of the data.dir directory
	base_dir = base_directory()

	#-- Opening output GRACE months HTML file
	filename = inspect.getframeinfo(inspect.currentframe()).filename
	filepath = os.path.dirname(os.path.abspath(filename))
	filename = 'GRACE-Months.html'
	fid = open(os.path.join(filepath,filename), 'w')

	#-- Initial parameters
	#-- processing centers
	proc = ['CSR', 'GFZ', 'JPL']
	#-- data releases
	if RL04:
		drel = ['4', '5']
	else:
		drel = ['5']
	#-- read from GSM datasets
	dset = 'GSM'
	#-- maximum month of the datasets
	#-- checks for the maximum month between processing centers
	max_mon = 0
	#-- contain the information for each dataset
	var_info = {}

	#-- Looping through data releases first (all RL04 then all RL05)
	#-- for each considered data release (RL04,RL05)
	for rl in drel:
		#-- for each processing centers (CSR, GFZ, JPL)
		for pr in proc:
			#-- Setting the data directory for processing center and release
			ddir = os.path.join(base_dir, 'grace.dir', '%s.dir' % pr, \
				'RL0%s.dir' % rl, '%s.dir' % dset)
			#-- read GRACE date ascii file
			#-- file created in read_grace.py or grace_dates.py
			datefile = os.path.join(ddir, '%s_RL0%s_DATES.txt' % (pr,rl))
			#-- skip the header line
			date_input = np.loadtxt(datefile, skiprows=1)
			#-- number of months
			nmon = np.shape(date_input)[0]

			#-- Setting the dictionary key e.g. 'CSR_RL04'
			var_name = '%s RL0%s' % (pr,rl)

			#-- Creating a python dictionary for each dataset with parameters:
			#-- month #, start year, start day, end year, end day
			#-- Purpose is to get all of the dates loaded for each dataset
			#-- Adding data to dictionary for data processing and release
			var_info[var_name] = {}
			#-- allocate for output variables
			var_info[var_name]['mon'] = np.zeros((nmon),dtype=np.int)
			var_info[var_name]['styr'] = np.zeros((nmon),dtype=np.int)
			var_info[var_name]['stday'] = np.zeros((nmon),dtype=np.int)
			var_info[var_name]['endyr'] = np.zeros((nmon),dtype=np.int)
			var_info[var_name]['endday'] = np.zeros((nmon),dtype=np.int)
			#-- place output variables in dictionary
			for i,key in enumerate(['mon','styr','stday','endyr','endday']):
				#-- first column is date in decimal form (start at 1 not 0)
				var_info[var_name][key] = date_input[:,i+1]
			#-- Finding the maximum month measured
			if (var_info[var_name]['mon'].max() > max_mon):
				#-- if the maximum month in this dataset is greater
				#-- than the previously read datasets
				max_mon = np.int(var_info[var_name]['mon'].max())

	#-- print HTML headers
	print >> fid, '<!DOCTYPE html>'
	print >> fid, '<html>'
	print >> fid, '\t<head>'
	print >> fid, '\t<meta charset="utf-8">'
	print >> fid, '\t<title>%s</title>' % filename
	print >> fid, '\t</head>'
	print >> fid, '\t<body id="preview">'
	print >> fid, '\t\t<table>'
	#-- print table header
	print >> fid, '\t\t<thead>'
	print >> fid, '\t\t<tr>'
	print >> fid, '\t\t\t<th style="text-align:center">Month</th>'
	print >> fid, '\t\t\t<th style="text-align:center">Date</th>'
	#-- sort datasets alphanumerically
	var_name = sorted(var_info.keys())
	for var in var_name:
		print >> fid, '\t\t\t<th style="text-align:center">%s</th>' % var
	print >> fid, '\t\t</tr>'
	print >> fid, '\t\t</thead>'
	#-- print table body
	print >> fid, '\t\t<tbody>'
	#-- for each possible month
	#-- GRACE starts at month 004 (April 2002)
	#-- max_mon+1 to include max_mon
	for m in range(4, max_mon+1):
		#-- finding the month name e.g. Apr
		#-- using an approximate mid-month date for the month
		month_str, = date_string([2002.+(m-0.5)/12.], SEP='')
		#-- create list object for output string
		output_string = []
		#-- for each processing center and data release
		for var in var_name:
			#-- find if the month of data exists
			#-- exists will be greater than 0 if there is a match
			exists = np.count_nonzero(var_info[var]['mon'] == m)
			if (exists != 0):
				#-- if there is a matching month
				#-- indice of matching month
				ind, = np.nonzero(var_info[var]['mon'] == m)
				#-- start date
				st_yr = var_info[var]['styr'][ind]
				st_day = var_info[var]['stday'][ind]
				#-- end date
				end_yr = var_info[var]['endyr'][ind]
				end_day = var_info[var]['endday'][ind]
				#-- output string is the date range
				#-- string format: 2002_102--2002_120
				output_string.append('%4i_%003i&ndash;%4i_%003i'
					% (st_yr, st_day, end_yr, end_day))
			else:
				#-- if there is no matching month = missing
				output_string.append('**missing**')

		#-- printing table lines to file
		print >> fid, '\t\t<tr>'
		print >> fid, '\t\t\t<td style="text-align:center">%003i</td>' % m
		print >> fid, '\t\t\t<td style="text-align:center">%s</td>' % month_str
		for s in output_string:
			print >> fid, '\t\t\t<td style="text-align:center">%s</td>' % s
		print >> fid, '\t\t</tr>'
	#-- print table body footer text
	print >> fid, '\t\t</tbody>'
	print >> fid, '\t\t</table>'

	#-- print footer text
	print >> fid, ('\n\t\t<p>Table created on %s with <a href="./%s">\n'
		'\t\t\t<code>%s</code></a></p>\n') % (date.isoformat(date.today()),
		os.path.basename(sys.argv[0]), os.path.basename(sys.argv[0]))

	#-- print HTML footers
	print >> fid, '\t</body>\n</html>\n'
	#-- close months file
	fid.close()

#-- PURPOSE: help module to describe the optional input parameters
def usage():
	print '\nHelp: %s' % os.path.basename(sys.argv[0])
	print ' --rl04\t\tInclude GRACE Release 4 Data\n'

#-- PURPOSE: functional call to grace_months() if running as program
def main():
	#-- Read the system arguments listed after the program
	optlist, input_files = getopt.getopt(sys.argv[1:],'h',['help','rl04'])

	#-- command line parameters
	RL04 = False
	for opt, arg in optlist:
		if opt in ('-h','--help'):
			usage()
			sys.exit()
		elif (opt == '--rl04'):
			RL04 = True

	#-- run grace months program
	grace_months(RL04=RL04)

#-- run main program
if __name__ == '__main__':
	main()

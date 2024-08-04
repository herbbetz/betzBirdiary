#!/bin/bash
# nach https://www.idnt.net/en-US/kb/941772
# read 5 secs of cpu load:
# Get the first line with aggregate of all CPUs 
cpu_now=($(head -n1 /proc/stat))
# Get all columns but skip the first (which is the "cpu" string) 
cpu_sum_now="${cpu_now[@]:1}" 
# Replace the column seperator (space) with + 
cpu_sum_now=$((${cpu_sum_now// /+}))
sleep 5
# second read:
cpu_then=($(head -n1 /proc/stat))
cpu_sum_then="${cpu_then[@]:1}"
cpu_sum_then=$((${cpu_sum_then// /+}))
# now the delta:
cpu_delta=$((cpu_sum_then - cpu_sum_now))
# Get the idle time Delta 
cpu_idle=$((cpu_then[4]- cpu_now[4]))
# Calc time spent working 
cpu_used=$((cpu_delta - cpu_idle))
# Calc percentage 
cpu_usage=$((100 * cpu_used / cpu_delta))
echo $cpu_usage
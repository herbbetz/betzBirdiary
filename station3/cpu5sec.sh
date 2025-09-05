#!/bin/bash
# measure CPU usage over 5 seconds

read -r _ user nice system idle iowait irq softirq steal guest guest_nice < /proc/stat
cpu_sum_now=$((user + nice + system + idle + iowait + irq + softirq + steal))
cpu_idle_now=$idle

sleep 5

read -r _ user nice system idle iowait irq softirq steal guest guest_nice < /proc/stat
cpu_sum_then=$((user + nice + system + idle + iowait + irq + softirq + steal))
cpu_idle_then=$idle

cpu_delta=$((cpu_sum_then - cpu_sum_now))
idle_delta=$((cpu_idle_then - cpu_idle_now))

if (( cpu_delta > 0 )); then
    cpu_usage=$((100 * (cpu_delta - idle_delta) / cpu_delta))
else
    cpu_usage=0
fi

echo "$cpu_usage"
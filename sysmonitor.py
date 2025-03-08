import os
import platform
import psutil
import datetime
import time
import sys
import argparse
import signal
from tabulate import tabulate
import matplotlib.pyplot as plt
import numpy as np
from collections import deque

# Global variables for resource history tracking
cpu_history = deque(maxlen=60)
memory_history = deque(maxlen=60)
network_sent_history = deque(maxlen=60)
network_recv_history = deque(maxlen=60)
disk_io_read_history = deque(maxlen=60)
disk_io_write_history = deque(maxlen=60)

class Spinner:
    """Simple spinner for showing progress"""
    def __init__(self):
        self.symbols = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.current = 0
        
    def next(self):
        """Returns the next spinner character"""
        symbol = self.symbols[self.current]
        self.current = (self.current + 1) % len(self.symbols)
        return symbol

def clear_screen():
    """Clears the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def show_ascii_art():
    """Displays the ASCII art for the system monitor"""
    ascii_art = """
    ███████╗██╗   ██╗███████╗████████╗███████╗███╗   ███╗    ███╗   ███╗ ██████╗ ███╗   ██╗██╗████████╗ ██████╗ ██████╗ 
    ██╔════╝╚██╗ ██╔╝██╔════╝╚══██╔══╝██╔════╝████╗ ████║    ████╗ ████║██╔═══██╗████╗  ██║██║╚══██╔══╝██╔═══██╗██╔══██╗
    ███████╗ ╚████╔╝ ███████╗   ██║   █████╗  ██╔████╔██║    ██╔████╔██║██║   ██║██╔██╗ ██║██║   ██║   ██║   ██║██████╔╝
    ╚════██║  ╚██╔╝  ╚════██║   ██║   ██╔══╝  ██║╚██╔╝██║    ██║╚██╔╝██║██║   ██║██║╚██╗██║██║   ██║   ██║   ██║██╔══██╗
    ███████║   ██║   ███████║   ██║   ███████╗██║ ╚═╝ ██║    ██║ ╚═╝ ██║╚██████╔╝██║ ╚████║██║   ██║   ╚██████╔╝██║  ██║
    ╚══════╝   ╚═╝   ╚══════╝   ╚═╝   ╚══════╝╚═╝     ╚═╝    ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝
    """
    print(ascii_art)
    print("\n" + "=" * 100)
    print("System Monitoring Tool".center(100))
    print("=" * 100 + "\n")

def get_system_info():
    """Retrieves basic system information"""
    info = {}
    info["system"] = platform.system()
    info["version"] = platform.version()
    info["processor"] = platform.processor()
    info["architecture"] = platform.architecture()[0]
    info["hostname"] = platform.node()
    info["python_version"] = platform.python_version()
    
    # Add more detailed information
    if platform.system() == "Windows":
        info["windows_edition"] = platform.win32_edition() if hasattr(platform, 'win32_edition') else "N/A"
    elif platform.system() == "Linux":
        try:
            with open('/etc/os-release') as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith('PRETTY_NAME='):
                        info["linux_distro"] = line.split('=')[1].strip().strip('"')
                        break
        except:
            info["linux_distro"] = "Unknown"
    elif platform.system() == "Darwin":
        info["mac_version"] = platform.mac_ver()[0]
    
    # Get boot time
    try:
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        info["boot_time"] = boot_time.strftime("%Y-%m-%d %H:%M:%S")
        uptime = datetime.datetime.now() - boot_time
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        info["uptime"] = f"{uptime.days} days, {hours} hours, {minutes} minutes"
    except:
        info["boot_time"] = "N/A"
        info["uptime"] = "N/A"
    
    return info

def get_resource_usage():
    """Retrieves current resource usage statistics"""
    resources = {}
    
    # CPU
    resources["cpu_percent"] = psutil.cpu_percent(interval=1)
    resources["cpu_freq"] = psutil.cpu_freq().current if hasattr(psutil.cpu_freq(), 'current') else "N/A"
    resources["cpu_physical_cores"] = psutil.cpu_count(logical=False)
    resources["cpu_logical_cores"] = psutil.cpu_count(logical=True)
    
    # Get per-core usage
    resources["per_core_percent"] = psutil.cpu_percent(interval=0.1, percpu=True)
    
    # CPU temperature (if available)
    if hasattr(psutil, "sensors_temperatures"):
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current > 0:  # Filter out zero readings
                            resources["cpu_temp"] = f"{entry.current}°C"
                            break
        except:
            resources["cpu_temp"] = "N/A"
    else:
        resources["cpu_temp"] = "N/A"
    
    # Memory
    mem = psutil.virtual_memory()
    resources["mem_total"] = mem.total
    resources["mem_available"] = mem.available
    resources["mem_percent"] = mem.percent
    resources["mem_used"] = mem.used
    
    # Swap memory
    swap = psutil.swap_memory()
    resources["swap_total"] = swap.total
    resources["swap_used"] = swap.used
    resources["swap_percent"] = swap.percent
    
    # Disk
    disks = []
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disks.append({
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "filesystem": partition.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent
            })
        except:
            # Some partitions may not be accessible
            pass
    resources["disks"] = disks
    
    # Disk I/O
    try:
        disk_io = psutil.disk_io_counters()
        resources["disk_read_bytes"] = disk_io.read_bytes
        resources["disk_write_bytes"] = disk_io.write_bytes
        resources["disk_read_count"] = disk_io.read_count
        resources["disk_write_count"] = disk_io.write_count
    except:
        resources["disk_read_bytes"] = "N/A"
        resources["disk_write_bytes"] = "N/A"
        resources["disk_read_count"] = "N/A"
        resources["disk_write_count"] = "N/A"
    
    # Network
    try:
        if hasattr(psutil, 'net_io_counters'):
            net = psutil.net_io_counters()
            resources["net_bytes_sent"] = net.bytes_sent
            resources["net_bytes_recv"] = net.bytes_recv
            resources["net_packets_sent"] = net.packets_sent
            resources["net_packets_recv"] = net.packets_recv
            resources["net_errin"] = net.errin
            resources["net_errout"] = net.errout
        else:
            resources["net_bytes_sent"] = "N/A"
            resources["net_bytes_recv"] = "N/A"
            resources["net_packets_sent"] = "N/A"
            resources["net_packets_recv"] = "N/A"
            resources["net_errin"] = "N/A"
            resources["net_errout"] = "N/A"
    except:
        resources["net_bytes_sent"] = "N/A"
        resources["net_bytes_recv"] = "N/A"
        resources["net_packets_sent"] = "N/A"
        resources["net_packets_recv"] = "N/A"
        resources["net_errin"] = "N/A"
        resources["net_errout"] = "N/A"
    
    # Network interfaces
    resources["network_interfaces"] = []
    try:
        for interface_name, interface_addresses in psutil.net_if_addrs().items():
            for address in interface_addresses:
                if address.family == socket.AF_INET:
                    resources["network_interfaces"].append({
                        "interface": interface_name,
                        "ip": address.address,
                        "netmask": address.netmask,
                    })
    except:
        pass
        
    # Battery (if applicable)
    if hasattr(psutil, "sensors_battery"):
        try:
            battery = psutil.sensors_battery()
            if battery:
                resources["battery_percent"] = battery.percent
                resources["battery_power_plugged"] = battery.power_plugged
                resources["battery_time_left"] = str(datetime.timedelta(seconds=battery.secsleft)) if battery.secsleft > 0 else "N/A"
            else:
                resources["battery_percent"] = "N/A"
                resources["battery_power_plugged"] = "N/A"
                resources["battery_time_left"] = "N/A"
        except:
            resources["battery_percent"] = "N/A"
            resources["battery_power_plugged"] = "N/A"
            resources["battery_time_left"] = "N/A"
    else:
        resources["battery_percent"] = "N/A"
        resources["battery_power_plugged"] = "N/A"
        resources["battery_time_left"] = "N/A"
    
    # Processes
    resources["total_processes"] = len(list(psutil.process_iter()))
    
    # Update history data
    cpu_history.append(resources["cpu_percent"])
    memory_history.append(resources["mem_percent"])
    
    if resources["net_bytes_sent"] != "N/A":
        network_sent_history.append(resources["net_bytes_sent"])
        network_recv_history.append(resources["net_bytes_recv"])
    
    if resources["disk_read_bytes"] != "N/A":
        disk_io_read_history.append(resources["disk_read_bytes"])
        disk_io_write_history.append(resources["disk_write_bytes"])
    
    return resources

def get_top_processes(sort_by="cpu"):
    """Retrieves top processes by CPU or memory usage
    
    Args:
        sort_by: Either "cpu" or "memory" to determine sorting method
    """
    processes = []
    
    if sort_by == "cpu":
        sort_key = "cpu_percent"
    else:
        sort_key = "memory_percent"
    
    for proc in sorted(
        psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status', 'create_time']), 
        key=lambda p: p.info[sort_key], 
        reverse=True
    )[:15]:  # Get top 15 processes
        try:
            # Get process creation time
            create_time = datetime.datetime.fromtimestamp(proc.info['create_time']).strftime("%Y-%m-%d %H:%M")
            
            # Get command line (first 30 chars)
            try:
                cmdline = " ".join(proc.cmdline())[:30] + ('...' if len(" ".join(proc.cmdline())) > 30 else '')
            except:
                cmdline = "N/A"
                
            processes.append({
                "pid": proc.info['pid'],
                "name": proc.info['name'],
                "user": proc.info['username'],
                "status": proc.info['status'],
                "cpu_percent": proc.info['cpu_percent'],
                "memory_percent": proc.info['memory_percent'],
                "created": create_time,
                "command": cmdline
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return processes

def check_system_issues(resources):
    """Checks for potential system issues based on thresholds"""
    issues = []
    
    # High CPU usage
    if resources["cpu_percent"] > 85:
        issues.append({
            "severity": "HIGH",
            "component": "CPU",
            "message": f"CPU usage is critically high at {resources['cpu_percent']}%."
        })
    elif resources["cpu_percent"] > 70:
        issues.append({
            "severity": "MEDIUM",
            "component": "CPU",
            "message": f"CPU usage is elevated at {resources['cpu_percent']}%."
        })
    
    # Low memory
    free_mem_percent = 100 - resources["mem_percent"]
    if free_mem_percent < 10:
        issues.append({
            "severity": "HIGH",
            "component": "Memory",
            "message": f"Available memory is critically low at {free_mem_percent}% free."
        })
    elif free_mem_percent < 20:
        issues.append({
            "severity": "MEDIUM",
            "component": "Memory",
            "message": f"Available memory is running low at {free_mem_percent}% free."
        })
    
    # High swap usage
    if resources["swap_percent"] > 80:
        issues.append({
            "severity": "MEDIUM",
            "component": "Swap",
            "message": f"Swap memory usage is high at {resources['swap_percent']}%, which may impact system performance."
        })
    
    # Low disk space
    for disk in resources["disks"]:
        if disk["percent"] > 90:
            issues.append({
                "severity": "HIGH",
                "component": "Disk",
                "message": f"Critically low disk space on {disk['mountpoint']} ({disk['percent']}% used, only {format_bytes(disk['free'])} free)."
            })
        elif disk["percent"] > 80:
            issues.append({
                "severity": "MEDIUM",
                "component": "Disk",
                "message": f"Low disk space on {disk['mountpoint']} ({disk['percent']}% used, {format_bytes(disk['free'])} free)."
            })
    
    # Battery check
    if resources["battery_percent"] != "N/A" and not resources["battery_power_plugged"]:
        if resources["battery_percent"] < 15:
            issues.append({
                "severity": "HIGH",
                "component": "Battery",
                "message": f"Battery level is critically low at {resources['battery_percent']}%. Connect to a power source soon."
            })
        elif resources["battery_percent"] < 30:
            issues.append({
                "severity": "MEDIUM",
                "component": "Battery",
                "message": f"Battery level is low at {resources['battery_percent']}%."
            })
    
    # High temperature check
    if resources["cpu_temp"] != "N/A":
        temp = float(resources["cpu_temp"].replace("°C", ""))
        if temp > 85:
            issues.append({
                "severity": "HIGH",
                "component": "Temperature",
                "message": f"CPU temperature is critically high at {resources['cpu_temp']}."
            })
        elif temp > 75:
            issues.append({
                "severity": "MEDIUM",
                "component": "Temperature",
                "message": f"CPU temperature is elevated at {resources['cpu_temp']}."
            })
    
    return issues

def format_bytes(bytes_value):
    """Converts bytes to a human-readable format (KB, MB, GB, etc.)"""
    if bytes_value == "N/A":
        return "N/A"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024
    return f"{bytes_value:.2f} PB"

def format_rate(bytes_value, time_sec=1):
    """Formats a rate (bytes per second) into a human-readable format"""
    if bytes_value == "N/A":
        return "N/A"
    
    return format_bytes(bytes_value) + "/s"

def calculate_rate(current, previous, interval=1):
    """Calculates the rate of change between two measurements"""
    if current == "N/A" or previous == "N/A":
        return "N/A"
    
    return (current - previous) / interval

def show_menu():
    """Displays the main menu"""
    print("\nOPTIONS:")
    print("1. Show System Information")
    print("2. Monitor Resources in Real-time")
    print("3. Check System Issues")
    print("4. View Top Processes")
    print("5. Generate Complete Report")
    print("6. Resource Usage Graphs")
    print("7. Monitor Selected Process")
    print("8. Network Connections")
    print("9. Disk I/O Statistics")
    print("0. Exit")
    return input("\nSelect an option (0-9): ")

def show_system_info(info):
    """Displays system information"""
    print("\n--- SYSTEM INFORMATION ---")
    print(f"Operating System: {info['system']} {info['version']}")
    
    # Display OS-specific info
    if "windows_edition" in info:
        print(f"Windows Edition: {info['windows_edition']}")
    if "linux_distro" in info:
        print(f"Linux Distribution: {info['linux_distro']}")
    if "mac_version" in info:
        print(f"macOS Version: {info['mac_version']}")
    
    print(f"Processor: {info['processor']}")
    print(f"Architecture: {info['architecture']}")
    print(f"Hostname: {info['hostname']}")
    print(f"Boot Time: {info['boot_time']}")
    print(f"System Uptime: {info['uptime']}")
    print(f"Python Version: {info['python_version']}")
    
def show_resource_usage(resources, previous_resources=None):
    """Displays system resource usage information"""
    print("\n--- RESOURCE USAGE ---")
    print(f"CPU: {resources['cpu_percent']}% | Frequency: {resources['cpu_freq']} MHz | Temperature: {resources['cpu_temp']}")
    print(f"Cores: {resources['cpu_physical_cores']} physical, {resources['cpu_logical_cores']} logical")
    
    # Show per-core usage
    cores_str = " ".join([f"Core {i}: {p}%" for i, p in enumerate(resources['per_core_percent'])])
    print(f"Per-core Usage: {cores_str}")
    
    print(f"\nTotal Memory: {format_bytes(resources['mem_total'])}")
    print(f"Used Memory: {format_bytes(resources['mem_used'])} ({resources['mem_percent']}%)")
    print(f"Available Memory: {format_bytes(resources['mem_available'])}")
    
    print(f"\nSwap Memory: {format_bytes(resources['swap_used'])} / {format_bytes(resources['swap_total'])} ({resources['swap_percent']}%)")
    
    print("\nDisks:")
    for i, disk in enumerate(resources['disks'], 1):
        print(f"  Disk {i}: {disk['device']} ({disk['filesystem']})")
        print(f"    Mount point: {disk['mountpoint']}")
        print(f"    Total space: {format_bytes(disk['total'])}")
        print(f"    Used: {format_bytes(disk['used'])} ({disk['percent']}%)")
        print(f"    Free: {format_bytes(disk['free'])}")
    
    # Show disk I/O rates if we have previous measurements
    if previous_resources and resources["disk_read_bytes"] != "N/A" and previous_resources["disk_read_bytes"] != "N/A":
        read_rate = calculate_rate(resources["disk_read_bytes"], previous_resources["disk_read_bytes"])
        write_rate = calculate_rate(resources["disk_write_bytes"], previous_resources["disk_write_bytes"])
        print(f"\nDisk I/O - Read Rate: {format_rate(read_rate)}")
        print(f"Disk I/O - Write Rate: {format_rate(write_rate)}")
    else:
        print(f"\nDisk I/O - Total Read: {format_bytes(resources['disk_read_bytes'])}")
        print(f"Disk I/O - Total Written: {format_bytes(resources['disk_write_bytes'])}")
    
    # Show network rates if we have previous measurements
    if previous_resources and resources["net_bytes_sent"] != "N/A" and previous_resources["net_bytes_sent"] != "N/A":
        sent_rate = calculate_rate(resources["net_bytes_sent"], previous_resources["net_bytes_sent"])
        recv_rate = calculate_rate(resources["net_bytes_recv"], previous_resources["net_bytes_recv"])
        print(f"\nNetwork - Upload Rate: {format_rate(sent_rate)}")
        print(f"Network - Download Rate: {format_rate(recv_rate)}")
    else:
        print(f"\nNetwork - Total Sent: {format_bytes(resources['net_bytes_sent'])}")
        print(f"Network - Total Received: {format_bytes(resources['net_bytes_recv'])}")
    
    # Battery information (if available)
    if resources["battery_percent"] != "N/A":
        status = "Plugged In" if resources["battery_power_plugged"] else "Discharging"
        time_left = resources["battery_time_left"] if not resources["battery_power_plugged"] else "N/A"
        print(f"\nBattery: {resources['battery_percent']}% - {status}")
        if time_left != "N/A":
            print(f"Estimated time remaining: {time_left}")
    
    print(f"\nActive Processes: {resources['total_processes']}")

def show_processes(processes, sort_by="cpu"):
    """Displays the top processes by CPU or memory usage"""
    print(f"\n--- TOP PROCESSES (Sorted by {sort_by.upper()}) ---")
    
    headers = ["PID", "Name", "User", "Status", "CPU %", "Memory %", "Created", "Command"]
    table_data = []
    
    for p in processes:
        table_data.append([
            p["pid"],
            p["name"],
            p["user"],
            p["status"],
            f"{p['cpu_percent']:.1f}",
            f"{p['memory_percent']:.1f}",
            p["created"],
            p["command"]
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="pretty"))

def generate_report():
    """Generates a complete report and saves it to a file"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"system_report_{timestamp}.txt"
    
    print(f"\nGenerating complete report: {filename}")
    
    spinner = Spinner()
    print("Please wait ", end="", flush=True)
    
    info = get_system_info()
    print(f"\rPlease wait {spinner.next()}", end="", flush=True)
    
    resources = get_resource_usage()
    print(f"\rPlease wait {spinner.next()}", end="", flush=True)
    
    cpu_processes = get_top_processes(sort_by="cpu")
    print(f"\rPlease wait {spinner.next()}", end="", flush=True)
    
    memory_processes = get_top_processes(sort_by="memory")
    print(f"\rPlease wait {spinner.next()}", end="", flush=True)
    
    issues = check_system_issues(resources)
    print(f"\rPlease wait {spinner.next()}", end="", flush=True)
    
    # Get network connections
    network_connections = []
    try:
        for conn in psutil.net_connections(kind='inet'):
            try:
                process = psutil.Process(conn.pid) if conn.pid else None
                network_connections.append({
                    "protocol": "TCP" if conn.type == socket.SOCK_STREAM else "UDP",
                    "local_addr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A",
                    "remote_addr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A",
                    "status": conn.status,
                    "pid": conn.pid,
                    "process_name": process.name() if process else "N/A"
                })
            except:
                pass
    except:
        pass
    
    print(f"\rPlease wait {spinner.next()}", end="", flush=True)
    
    # Get users logged in
    users = []
    try:
        for user in psutil.users():
            users.append({
                "name": user.name,
                "terminal": user.terminal,
                "host": user.host,
                "started": datetime.datetime.fromtimestamp(user.started).strftime("%Y-%m-%d %H:%M:%S")
            })
    except:
        pass
    
    print(f"\rWriting report... ", end="", flush=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("SYSTEM STATUS REPORT\n")
        f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        # System information
        f.write("SYSTEM INFORMATION\n")
        f.write("-" * 30 + "\n")
        f.write(f"Operating System: {info['system']} {info['version']}\n")
        
        # OS-specific info
        if "windows_edition" in info:
            f.write(f"Windows Edition: {info['windows_edition']}\n")
        if "linux_distro" in info:
            f.write(f"Linux Distribution: {info['linux_distro']}\n")
        if "mac_version" in info:
            f.write(f"macOS Version: {info['mac_version']}\n")
        
        f.write(f"Processor: {info['processor']}\n")
        f.write(f"Architecture: {info['architecture']}\n")
        f.write(f"Hostname: {info['hostname']}\n")
        f.write(f"Boot Time: {info['boot_time']}\n")
        f.write(f"System Uptime: {info['uptime']}\n")
        f.write(f"Python Version: {info['python_version']}\n\n")
        
        # Resource usage
        f.write("RESOURCE USAGE\n")
        f.write("-" * 30 + "\n")
        f.write(f"CPU: {resources['cpu_percent']}% | Frequency: {resources['cpu_freq']} MHz | Temperature: {resources['cpu_temp']}\n")
        f.write(f"Cores: {resources['cpu_physical_cores']} physical, {resources['cpu_logical_cores']} logical\n")
        
        # Per-core usage
        f.write("Per-core Usage:\n")
        for i, p in enumerate(resources['per_core_percent']):
            f.write(f"  Core {i}: {p}%\n")
        
        f.write(f"\nTotal Memory: {format_bytes(resources['mem_total'])}\n")
        f.write(f"Used Memory: {format_bytes(resources['mem_used'])} ({resources['mem_percent']}%)\n")
        f.write(f"Available Memory: {format_bytes(resources['mem_available'])}\n")
        
        f.write(f"\nSwap Memory: {format_bytes(resources['swap_used'])} / {format_bytes(resources['swap_total'])} ({resources['swap_percent']}%)\n")
        
        f.write("\nDisks:\n")
        for i, disk in enumerate(resources['disks'], 1):
            f.write(f"  Disk {i}: {disk['device']} ({disk['filesystem']})\n")
            f.write(f"    Mount point: {disk['mountpoint']}\n")
            f.write(f"    Total space: {format_bytes(disk['total'])}\n")
            f.write(f"    Used: {format_bytes(disk['used'])} ({disk['percent']}%)\n")
            f.write(f"    Free: {format_bytes(disk['free'])}\n")
        
        f.write(f"\nDisk I/O - Total Read: {format_bytes(resources['disk_read_bytes'])}\n")
        f.write(f"Disk I/O - Total Written: {format_bytes(resources['disk_write_bytes'])}\n")
        f.write(f"Disk I/O - Read Operations: {resources['disk_read_count']}\n")
        f.write(f"Disk I/O - Write Operations: {resources['disk_write_count']}\n")
        
        f.write(f"\nNetwork - Total Sent: {format_bytes(resources['net_bytes_sent'])}\n")
        f.write(f"Network - Total Received: {format_bytes(resources['net_bytes_recv'])}\n")
        f.write(f"Network - Packets Sent: {resources['net_packets_sent']}\n")
        f.write(f"Network - Packets Received: {resources['net_packets_recv']}\n")
        f.write(f"Network - Inbound Errors: {resources['net_errin']}\n")
        f.write(f"Network - Outbound Errors: {resources['net_errout']}\n")
        
        # Network interfaces
        f.write("\nNetwork Interfaces:\n")
        for iface in resources.get("network_interfaces", []):
            f.write(f"  Interface: {iface['interface']}\n")
            f.write(f"    IP: {iface['ip']}\n")
            f.write(f"    Netmask: {iface['netmask']}\n")
        
        # Battery information (if available)
        if resources["battery_percent"] != "N/A":
            status = "Plugged In" if resources["battery_power_plugged"] else "Discharging"
            time_left = resources["battery_time_left"] if not resources["battery_power_plugged"] else "N/A"
            f.write(f"\nBattery: {resources['battery_percent']}% - {status}\n")
            if time_left != "N/A":
                f.write(f"Estimated time remaining: {time_left}\n")
        
        f.write(f"\nActive Processes: {resources['total_processes']}\n\n")
        
        # System Issues
        f.write("SYSTEM ISSUES\n")
        f.write("-" * 30 + "\n")
        if issues:
            for issue in issues:
                f.write(f"[{issue['severity']}] {issue['component']}: {issue['message']}\n")
        else:
            f.write("No system issues detected.\n")
        f.write("\n")
        
        # Top processes by CPU
        f.write("TOP PROCESSES BY CPU USAGE\n")
        f.write("-" * 30 + "\n")
        f.write(f"{'PID':<7} {'Name':<20} {'User':<15} {'Status':<10} {'CPU %':<8} {'Memory %':<10} {'Created':<16} {'Command':<40}\n")
        for p in cpu_processes:
            f.write(f"{p['pid']:<7} {p['name'][:20]:<20} {p['user'][:15]:<15} {p['status'][:10]:<10} {p['cpu_percent']:<8.1f} {p['memory_percent']:<10.1f} {p['created']:<16} {p['command'][:40]:<40}\n")
        f.write("\n")
        
        # Top processes by memory
        f.write("TOP PROCESSES BY MEMORY USAGE\n")
        f.write("-" * 30 + "\n")
        f.write(f"{'PID':<7} {'Name':<20} {'User':<15} {'Status':<10} {'CPU %':<8} {'Memory %':<10} {'Created':<16} {'Command':<40}\n")
        for p in memory_processes:
            f.write(f"{p['pid']:<7} {p['name'][:20]:<20} {p['user'][:15]:<15} {p['status'][:10]:<10} {p['cpu_percent']:<8.1f} {p['memory_percent']:<10.1f} {p['created']:<16} {p['command'][:40]:<40}\n")
        f.write("\n")
        
        # Network connections
        f.write("NETWORK CONNECTIONS\n")
        f.write("-" * 30 + "\n")
        if network_connections:
            f.write(f"{'Protocol':<8} {'Local Address':<25} {'Remote Address':<25} {'Status':<15} {'PID':<7} {'Process':<20}\n")
            for conn in network_connections[:30]:  # Limit to 30 connections
                f.write(f"{conn['protocol']:<8} {conn['local_addr'][:25]:<25} {conn['remote_addr'][:25]:<25} {conn['status'][:15]:<15} {conn['pid'] if conn['pid'] else 'N/A':<7} {conn['process_name'][:20]:<20}\n")
        else:
            f.write("No network connections information available.\n")
        f.write("\n")
        
        # Logged in users
        f.write("LOGGED IN USERS\n")
        f.write("-" * 30 + "\n")
        if users:
            f.write(f"{'User':<20} {'Terminal':<15} {'Host':<30} {'Login Time':<20}\n")
            for user in users:
                f.write(f"{user['name'][:20]:<20} {user['terminal'][:15]:<15} {user['host'][:30]:<30} {user['started']:<20}\n")
        else:
            f.write("No user login information available.\n")
    
    print(f"\rReport generated and saved as: {filename}    ")
    return filename

def monitor_live():
    """Monitors resources in real-time with continuous updates"""
    try:
        interval = 2  # Update every 2 seconds
        previous_resources = None
        
        print("\nPress Ctrl+C to stop monitoring...")
        time.sleep(1)
        
        while True:
            clear_screen()
            resources = get_resource_usage()
            
            print("--- LIVE SYSTEM MONITORING ---")
            print(f"Press Ctrl+C to stop | Last update: {datetime.datetime.now().strftime('%H:%M:%S')}")
            
            show_resource_usage(resources, previous_resources)
            
            # Keep track of previous resources for rate calculations
            previous_resources = resources
            
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

def monitor_process():
    """Monitors a specific process by PID"""
    try:
        pid = int(input("\nEnter the Process ID (PID) to monitor: "))
        process = psutil.Process(pid)
        
        print(f"\nMonitoring process: {process.name()} (PID: {pid})")
        print("Press Ctrl+C to stop monitoring...")
        time.sleep(1)
        
        interval = 1  # Update every second
        
        # Create history deques for this process
        process_cpu_history = deque(maxlen=60)
        process_memory_history = deque(maxlen=60)
        
        while True:
            clear_screen()
            try:
                # Get process info
                with process.oneshot():
                    cpu_percent = process.cpu_percent(interval=0.1)
                    memory_percent = process.memory_percent()
                    memory_info = process.memory_info()
                    status = process.status()
                    create_time = datetime.datetime.fromtimestamp(process.create_time()).strftime("%Y-%m-%d %H:%M:%S")
                    running_time = datetime.datetime.now() - datetime.datetime.fromtimestamp(process.create_time())
                    hours, remainder = divmod(running_time.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    running_time_str = f"{running_time.days} days, {hours} hours, {minutes} minutes, {seconds} seconds"
                    io_counters = process.io_counters() if hasattr(process, 'io_counters') else None
                    threads = process.num_threads()
                    try:
                        cmdline = " ".join(process.cmdline())
                    except:
                        cmdline = "N/A"
                    
                    # Update history
                    process_cpu_history.append(cpu_percent)
                    process_memory_history.append(memory_percent)
                
                print(f"--- MONITORING PROCESS: {process.name()} (PID: {pid}) ---")
                print(f"Press Ctrl+C to stop | Last update: {datetime.datetime.now().strftime('%H:%M:%S')}")
                
                print(f"\nStatus: {status}")
                print(f"CPU Usage: {cpu_percent}%")
                print(f"Memory Usage: {memory_percent:.2f}% ({format_bytes(memory_info.rss)})")
                print(f"Created: {create_time}")
                print(f"Running Time: {running_time_str}")
                print(f"Threads: {threads}")
                
                if io_counters:
                    print(f"I/O - Read: {format_bytes(io_counters.read_bytes)}")
                    print(f"I/O - Written: {format_bytes(io_counters.write_bytes)}")
                
                print(f"\nCommand Line: {cmdline}")
                
                # Show mini CPU history graph using ASCII
                print("\nCPU Usage History (last 60 seconds):")
                show_ascii_graph(process_cpu_history, 50, 25)
                
                # Show mini memory history graph using ASCII
                print("\nMemory Usage History (last 60 seconds):")
                show_ascii_graph(process_memory_history, 50, 25)
                
                time.sleep(interval)
            except psutil.NoSuchProcess:
                print(f"\nProcess with PID {pid} terminated.")
                break
            except psutil.AccessDenied:
                print(f"\nAccess denied to process with PID {pid}.")
                break
    except psutil.NoSuchProcess:
        print(f"\nProcess with PID {pid} not found.")
    except ValueError:
        print("\nInvalid PID.")
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

def show_ascii_graph(data, width=50, height=10):
    """Displays an ASCII graph of the given data"""
    if not data:
        print("No data available")
        return
    
    # Create y-axis labels
    max_val = max(data) if data else 0
    min_val = min(data) if data else 0
    
    # Ensure we don't divide by zero
    if max_val == min_val:
        max_val += 1
    
    # Create the graph
    for h in range(height, 0, -1):
        threshold = min_val + (max_val - min_val) * h / height
        row = ""
        for value in data:
            if value >= threshold:
                row += "█"
            else:
                row += " "
        
        # Add y-axis label
        if h == height:
            label = f"{max_val:.1f}%"
        elif h == 1:
            label = f"{min_val:.1f}%"
        elif h == height // 2:
            mid_val = min_val + (max_val - min_val) / 2
            label = f"{mid_val:.1f}%"
        else:
            label = "       "
        
        print(f"{label} |{row}")
    
    # Add x-axis
    print("       " + "-" * len(data))
    
    # Add time markers
    if len(data) > 10:
        print("       " + "0s" + " " * (len(data) - 8) + f"-{len(data)}s")

def plot_resource_graphs():
    """Generates and displays graphs of resource usage"""
    if not plt:
        print("\nError: Matplotlib is required for this feature.")
        print("Install it with: pip install matplotlib")
        return
    
    print("\nGenerating resource usage graphs...")
    
    # Create a figure with multiple subplots
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('System Resource Usage History')
    
    # Time axis (last 60 points)
    time_labels = list(range(-len(cpu_history) + 1, 1))
    
    # Create CPU usage graph
    axs[0, 0].plot(time_labels, list(cpu_history), 'b-', linewidth=2)
    axs[0, 0].set_title('CPU Usage (%)')
    axs[0, 0].set_ylim(0, 100)
    axs[0, 0].set_xlabel('Time (seconds)')
    axs[0, 0].grid(True)
    
    # Create memory usage graph
    axs[0, 1].plot(time_labels, list(memory_history), 'r-', linewidth=2)
    axs[0, 1].set_title('Memory Usage (%)')
    axs[0, 1].set_ylim(0, 100)
    axs[0, 1].set_xlabel('Time (seconds)')
    axs[0, 1].grid(True)
    
    # Create network usage graph if we have data
    if network_sent_history:
        # Convert to KB/s for better readability
        sent_kb = [b/1024 for b in calculate_deltas(network_sent_history)]
        received_kb = [b/1024 for b in calculate_deltas(network_recv_history)]
        
        net_time_labels = list(range(-len(sent_kb) + 1, 1))
        axs[1, 0].plot(net_time_labels, sent_kb, 'g-', label='Upload')
        axs[1, 0].plot(net_time_labels, received_kb, 'm-', label='Download')
        axs[1, 0].set_title('Network Usage (KB/s)')
        axs[1, 0].set_xlabel('Time (seconds)')
        axs[1, 0].grid(True)
        axs[1, 0].legend()
    else:
        axs[1, 0].text(0.5, 0.5, 'No network data available', horizontalalignment='center',
                        verticalalignment='center', transform=axs[1, 0].transAxes)
    
    # Create disk I/O graph if we have data
    if disk_io_read_history:
        # Convert to KB/s for better readability
        read_kb = [b/1024 for b in calculate_deltas(disk_io_read_history)]
        write_kb = [b/1024 for b in calculate_deltas(disk_io_write_history)]
        
        io_time_labels = list(range(-len(read_kb) + 1, 1))
        axs[1, 1].plot(io_time_labels, read_kb, 'c-', label='Read')
        axs[1, 1].plot(io_time_labels, write_kb, 'y-', label='Write')
        axs[1, 1].set_title('Disk I/O (KB/s)')
        axs[1, 1].set_xlabel('Time (seconds)')
        axs[1, 1].grid(True)
        axs[1, 1].legend()
    else:
        axs[1, 1].text(0.5, 0.5, 'No disk I/O data available', horizontalalignment='center',
                        verticalalignment='center', transform=axs[1, 1].transAxes)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()

def calculate_deltas(data_history):
    """Calculate the delta between consecutive measurements"""
    if len(data_history) < 2:
        return []
    
    result = []
    for i in range(1, len(data_history)):
        result.append(data_history[i] - data_history[i-1])
    
    return result

def show_network_connections():
    """Displays current network connections"""
    print("\n--- NETWORK CONNECTIONS ---")
    
    try:
        connections = []
        for conn in psutil.net_connections(kind='inet'):
            try:
                process = psutil.Process(conn.pid) if conn.pid else None
                connections.append({
                    "protocol": "TCP" if conn.type == socket.SOCK_STREAM else "UDP",
                    "local_addr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A",
                    "remote_addr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A",
                    "status": conn.status,
                    "pid": conn.pid,
                    "process_name": process.name() if process else "N/A"
                })
            except:
                pass
        
        if connections:
            headers = ["Protocol", "Local Address", "Remote Address", "Status", "PID", "Process"]
            table_data = []
            
            for conn in connections:
                table_data.append([
                    conn['protocol'],
                    conn['local_addr'],
                    conn['remote_addr'],
                    conn['status'],
                    conn['pid'] if conn['pid'] else "N/A",
                    conn['process_name']
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="pretty"))
            print(f"\nTotal connections: {len(connections)}")
        else:
            print("No network connections information available.")
    except:
        print("Could not retrieve network connection information.")

def show_disk_io_stats():
    """Displays detailed disk I/O statistics"""
    print("\n--- DISK I/O STATISTICS ---")
    
    try:
        # Get disk I/O counters per disk
        disk_io = psutil.disk_io_counters(perdisk=True)
        
        if disk_io:
            headers = ["Device", "Read Count", "Read Bytes", "Read Time", "Write Count", "Write Bytes", "Write Time"]
            table_data = []
            
            for device, stats in disk_io.items():
                table_data.append([
                    device,
                    stats.read_count,
                    format_bytes(stats.read_bytes),
                    f"{stats.read_time}ms" if hasattr(stats, 'read_time') else "N/A",
                    stats.write_count,
                    format_bytes(stats.write_bytes),
                    f"{stats.write_time}ms" if hasattr(stats, 'write_time') else "N/A"
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="pretty"))
            
            # Get disk partitions
            print("\n--- DISK PARTITIONS ---")
            
            headers = ["Device", "Mountpoint", "Filesystem", "Options"]
            table_data = []
            
            for part in psutil.disk_partitions(all=True):
                table_data.append([
                    part.device,
                    part.mountpoint,
                    part.fstype,
                    part.opts
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="pretty"))
        else:
            print("No disk I/O information available.")
    except:
        print("Could not retrieve disk I/O statistics.")

def show_system_issues(resources):
    """Displays system issues and recommendations"""
    print("\n--- SYSTEM HEALTH CHECK ---")
    
    issues = check_system_issues(resources)
    
    if issues:
        print("\nDetected system issues:")
        
        headers = ["Severity", "Component", "Issue"]
        table_data = []
        
        for issue in issues:
            table_data.append([
                issue["severity"],
                issue["component"],
                issue["message"]
            ])
        
        print(tabulate(table_data, headers=headers, tablefmt="pretty"))
        
        # Provide recommendations
        print("\nRecommendations:")
        for issue in issues:
            if issue["component"] == "CPU" and issue["severity"] == "HIGH":
                print("- Consider closing resource-intensive applications")
                print("- Check for runaway processes and terminate them if necessary")
            elif issue["component"] == "Memory" and issue["severity"] in ["MEDIUM", "HIGH"]:
                print("- Close unnecessary applications to free up memory")
                print("- Consider upgrading RAM if this is a recurring issue")
            elif issue["component"] == "Disk" and issue["severity"] in ["MEDIUM", "HIGH"]:
                print("- Clean up unnecessary files")
                print("- Run disk cleanup utilities")
                print("- Consider moving files to external storage")
            elif issue["component"] == "Temperature" and issue["severity"] in ["MEDIUM", "HIGH"]:
                print("- Ensure proper ventilation for your device")
                print("- Clean cooling fans and vents")
                print("- Avoid using the device on soft surfaces that block airflow")
            elif issue["component"] == "Battery" and issue["severity"] in ["MEDIUM", "HIGH"]:
                print("- Connect to a power source soon")
                print("- Enable power saving mode")
    else:
        print("\nNo system issues detected. Your system appears to be healthy!")

def signal_handler(sig, frame):
    """Handles Ctrl+C signal to exit gracefully"""
    print("\nExiting...")
    sys.exit(0)

def main():
    """Main function"""
    # Register signal handler for graceful exit
    signal.signal(signal.SIGINT, signal_handler)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Advanced System Monitor')
    parser.add_argument('-m', '--monitor', action='store_true', help='Start live monitoring immediately')
    parser.add_argument('-r', '--report', action='store_true', help='Generate a report immediately')
    parser.add_argument('-i', '--info', action='store_true', help='Show system information and exit')
    args = parser.parse_args()
    
    # Handle command line arguments
    if args.monitor:
        monitor_live()
        return
    elif args.report:
        generate_report()
        return
    elif args.info:
        show_system_info(get_system_info())
        input("\nPress Enter to exit...")
        return
    
    # Import all required modules
    try:
        import socket
    except ImportError:
        print("Warning: socket module not available, some features may be limited.")
    
    # Main program loop
    while True:
        clear_screen()
        show_ascii_art()
        
        choice = show_menu()
        
        if choice == '0':
            print("\nExiting...")
            break
        elif choice == '1':
            show_system_info(get_system_info())
            input("\nPress Enter to continue...")
        elif choice == '2':
            monitor_live()
        elif choice == '3':
            resources = get_resource_usage()
            show_system_issues(resources)
            input("\nPress Enter to continue...")
        elif choice == '4':
            sort_option = input("\nSort by (1) CPU or (2) Memory? [1/2]: ")
            sort_by = "memory" if sort_option == "2" else "cpu"
            show_processes(get_top_processes(sort_by=sort_by), sort_by=sort_by)
            input("\nPress Enter to continue...")
        elif choice == '5':
            report_file = generate_report()
            input(f"\nReport saved to {report_file}. Press Enter to continue...")
        elif choice == '6':
            plot_resource_graphs()
        elif choice == '7':
            monitor_process()
        elif choice == '8':
            show_network_connections()
            input("\nPress Enter to continue...")
        elif choice == '9':
            show_disk_io_stats()
            input("\nPress Enter to continue...")
        else:
            print("\nInvalid choice. Please try again.")
            time.sleep(1)

if __name__ == "__main__":
    main()

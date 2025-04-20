from scapy.all import *
from threading import Thread

def capture_traffic(target_ip, capture_duration, pcap_file):
    print("Starting packet capture...")
    packets = sniff(filter=f"host {target_ip}", timeout=capture_duration)
    print(f"Captured {len(packets)} packets.")
    
    # Save the captured packets to a file
    if len(packets) > 0:
        wrpcap(pcap_file, packets)
        print(f"Packets saved to {pcap_file}")
    else:
        print("No packets captured, nothing to save.")

def ping_and_capture(target_ip):
    capture_duration = 10  # Capture duration in seconds
    pcap_file = "captured_traffic.pcap"  # File to save captured packets

    # Start packet capture in a separate thread
    capture_thread = Thread(target=capture_traffic, args=(target_ip, capture_duration, pcap_file))
    capture_thread.start()

    # Send an ICMP echo request to the target IP
    print(f"Sending ICMP ping to {target_ip}...")
    packet = IP(dst=target_ip)/ICMP()
    reply = sr1(packet, timeout=2, verbose=0)

    if reply:
        print(f"Received reply from {target_ip}:")
        reply.show()
    else:
        print(f"No reply from {target_ip}. Capturing traffic...")

    # Wait for the capture to finish
    capture_thread.join()

# Set the target IP address (VM's IP)
target_ip = "192.168.64.21"

# Run the function
ping_and_capture(target_ip)


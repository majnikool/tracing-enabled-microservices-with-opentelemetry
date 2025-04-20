from scapy.all import rdpcap

# Load the PCAP file
pcap_file = "/Users/Majid/tracing-enabled-microservices-with-opentelemetry/requirements/captured_traffic.pcap"
packets = rdpcap(pcap_file)

# Analyze the packets to look for ICMP or ping-related activity
icmp_packets = [pkt for pkt in packets if pkt.haslayer('ICMP')]

# Show a summary of the ICMP packets
icmp_summary = [pkt.summary() for pkt in icmp_packets]

icmp_summary[:10]  # Display the first 10 ICMP packet summaries

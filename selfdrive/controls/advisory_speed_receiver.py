import cereal.messaging as messaging
import socket

def main():
    pm = messaging.PubMaster(['advisorySpeed'])
    
    # Set up a UDP socket to receive speed data from the tablet
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('192.168.2.1', 9090))  # Comma 3X IP and the port number

    print("Listening for UDP packets on port 9090...")

    while True:
        try:
            # Receive data from the socket
            data, addr = udp_socket.recvfrom(1024)
            data = data.decode('utf-8').strip()
            if data:
                advisory_speed = float(data)  # Convert the string to float
                
                # Create and send the message using custom.AdvisorySpeed
                dat = messaging.new_message('advisorySpeed')
                dat.advisorySpeed.speed = advisory_speed
                pm.send('advisorySpeed', dat)
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()

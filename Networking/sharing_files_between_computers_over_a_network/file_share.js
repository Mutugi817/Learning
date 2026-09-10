/**
 * HOW OFFLINE LOCAL WIFI SHARING WORKS
 * 
 * 1. Local Area Network (LAN): Connect both laptops to the same Wi-Fi router (internet access is not required) OR turn on a Wi-Fi Hotspot on Laptop A and Connect Laptop B to it.
 * 
 * 2. Local IP Addressing: The router or hotspot assigns a local IP address (e.g., 192.168.1.15) to each device.
 * 
 * 3. TCP & HTTP Streaming: One laptop acts as the Receiver (hosts an HTTP server), and the other acts as the Sender (streams the file over TCP via an HTTP request).
 * 
 * 4. Zero-Buffer Memory Usage: Node.js users Streams (fs.ReadStream and fs.WriteStream). Instead of loading large files (e.g., a 10 GB file) into the system RAM, Node.js processes data in tiny chunks (typically 64 KB) directly from disk to network card.
 */

// The Receiver Script

const


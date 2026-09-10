# HOW OFFLINE LOCAL WIFI SHARING WORKS

Local Area Network (LAN): Connect both laptops to the same Wi-Fi router (internet access is not required) OR turn on a Wi-Fi Hotspot on Laptop A and Connect Laptop B to it.

Local IP Addressing: The router or hotspot assigns a local IP address (e.g., 192.168.1.15) to each device.

TCP & HTTP Streaming: One laptop acts as the Receiver (hosts an HTTP server), and the other acts as the Sender (streams the file over TCP via an HTTP request).

Zero-Buffer Memory Usage: Node.js users Streams (fs.ReadStream and fs.WriteStream). Instead of loading large files (e.g., a 10 GB file) into the system RAM, Node.js processes data in tiny chunks (typically 64 KB) directly from disk to network card.
 
## Step 1: The Receiver Script (receiver.js)

Run this script on the laptop that will receive files. It inspects the local network, finds its IP address, and starts an HTTP server listening for file streams.

```js
const http = require("http")
const fs = re

```
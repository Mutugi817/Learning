const http = require("http")
const fs = require('fs')
const path = require('path')
const os = require('os')

const PORT = 8080
const UPLOAD_DIR = path.join(__dirname, 'received_files')

// Automatically detects the device's local IP address on WI-FI/LAN
function getLocalIP() {
    const interfaces = os.networkInterfaces();
    for (const name in interfaces) {
        for (const net of interfaces[name]) {
            if (net.family === 'IPv4' && !net.internal) {
                return net.address
            }
        }
    }
    return '127.0.0.1'
}

// Ensure the directory to store files exists
if (!fs.existsSync(UPLOAD_DIR)) {
    fs.mkdirSync(UPLOAD_DIR)
}

// Create the HTTP server 
const server = http.createServer((req, res) => {
    if (req.method === 'POST') {
        // Extranct original filename sent in request header
        const filename = req.headers['x-filename'] || `file_${Date.now()}`
        const savePath = path.join(UPLOAD_DIR, path.basename(filename))

        console.log(`\n[+] Incoming transfer: "${filename}"`)

        // Create a writable file streams on disk
        const writeStream = fs.createWriteStream(savePath)

        // Pipe the incomming HTTP network socket stream directly to disk
        req.pipe(writeStream)

        // Event: Fired when the network transfer finishes
        req.on('end', () => {
            console.log(`[✔] File saved successfully to: ${savePath}`)
            res.writeHead(200, {
                'Content-Type': 'text/plain'
            })
            res.end('Upload completed successfully.')
        })

        // Event: Handle disk write errors
        writeStream.on('error', (error) => {
            console.error(`[!] Disk Write Error:`, error.message)
            res.writeHead(500)
            res.end('Failed to save file')
        })
    } else {
        res.writeHead(405)
        res.end('Only POSt requests allowed')
    }
})


server.listen(PORT, () => {
    console.log(`========================================`);
    console.log(` RECEIVER READY (Offline Wi-Fi Share)`);
    console.log(`========================================`);
    console.log(`Local IP Address: ${getLocalIP()}`);
    console.log(`Port            : ${PORT}`);
    console.log(`Saving files to : ${UPLOAD_DIR}`);
    console.log(`Waiting for sender...`);
})
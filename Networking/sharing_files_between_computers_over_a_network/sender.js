const http = require('http')
const fs = require('fs')
const path = require('path')

// Read command line arguments: node sender.js <RECEIVER_IP> <FILE_PATH>
const [, , receiverIP, filePath] = process.argv

if (!receiverIP || !filePath) {
    console.log('Usage: node sender.js <RECEIVER_IP> <FILE_PATH>')
    console.log('Example: node sender.js 192.168.1.15 ./video.mp4')
    process.exit(1)
}

if (!fs.existsSync(filePath)) {
    console.log(`[!] Error: File does not exists.`)
    process.exit(1)
}



// Gather file details
const fileStats = fs.statSync(filePath)
const totalSizeBytes = fileStats.size
const filename = path.basename(filePath)

let uploadedBytes = 0

// Create readable stream from local disk
const readStream = fs.createReadStream(filePath)

// HTTP Request Configuration
const options = {
    hostname: receiverIP,
    port: 8080,
    path: '/upload',
    method: 'POST',
    headers: {
        'Content-Type': 'application/octet-stream',
        'Content-Length': totalSizeBytes,
        'x-filename': filename
    }
}

// Initialize HTTP Client Connection
const req = http.request(options, (res) => {
    let responseData = ''
    res.on('data', chuck => responseData += chuck)
    res.on('end', () => {
        console.log(`\n[✔] Transfer complet. Receiver output: ${responseData}`)
    })
})

req.on('error', (error) => {
    console.error('[!] Network Transfer Failed: ', error.message)
})

// Track transfer progress
readStream.on('data', (chunk) => {
    uploadedBytes += chunk.length
    const progress = ((uploadedBytes / totalSizeBytes) * 100).toFixed(2)
    const uploadedMB = (uploadedBytes / (1024 * 1024).toFixed(2))
    const totalMB = (totalSizeBytes / (1024 * 1024)).toFixed(2)

    process.stdout.write(`Transferring: ${progress}% (${uploadedMB} MB / ${totalMB} MB)\r`)
})


// Pipe local file stream directoly into HTTP request stream
readStream.pipe(req)
// gps-server.js

const fs = require("fs");
const path = require("path");

// ======================================================
// LOG DIRECTORY
// ======================================================

const logDir = path.join(__dirname, "logs");

if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir);
}

const logFile = path.join(logDir, "gps.log");

// ======================================================
// GLOBAL VARIABLES
// ======================================================

let serial = 100;

// ======================================================
// FIXED 10 GPS DEVICES
// ======================================================

const imeiPool = [
    "867440069564321",
    "867440069564322",
    "867440069564323",
    "867440069564324",
    "867440069564325",
    "867440069564326",
    "867440069564327",
    "867440069564328",
    "867440069564329",
    "867440069564330"
];

// ======================================================
// HELPERS
// ======================================================

function rand(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function now() {

    const d = new Date();

    const yyyy = d.getFullYear();
    const MM = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");

    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    const ss = String(d.getSeconds()).padStart(2, "0");

    return `${yyyy}/${MM}/${dd} ${hh}:${mm}:${ss}`;
}

function randomHex(length) {

    const chars = "0123456789ABCDEF";

    let out = "";

    for (let i = 0; i < length; i++) {
        out += chars[rand(0, chars.length - 1)];
    }

    return out;
}

function randomIP() {

    return `${rand(1,255)}.${rand(1,255)}.${rand(1,255)}.${rand(1,255)}`;
}

function randomIMEI() {

    return imeiPool[rand(0, imeiPool.length - 1)];
}

function randomLat() {

    return (22.50 + Math.random() * 0.2).toFixed(6);
}

function randomLon() {

    return (88.30 + Math.random() * 0.3).toFixed(6);
}

function log(message) {

    const output = `${now()} ${message}`;

    console.log(output);

    fs.appendFileSync(logFile, output + "\n");
}

// ======================================================
// PACKET TYPES
// ======================================================

function serverListening() {

    log(`Server listening on :5023`);
}

function loginPacket() {

    const imei = randomIMEI();

    log(`Client connected: ${randomIP()}:${rand(10000,60000)}`);

    log(`Received: ${randomHex(40)}`);

    log(`serial ${serial}`);

    log(`Processing protocol: 0x01 `);

    log(`✅ Login packet - IMEI: ${imei}, Serial: ${serial}`);

    log(`Sent response: ${randomHex(20)}`);

    serial++;
}

function heartbeatPacket() {

    const imei = randomIMEI();

    log(`Received: ${randomHex(32)}`);

    log(`serial ${serial}`);

    log(`Processing protocol: 0x13 `);

    log(
        `✅ Heartbeat - IMEI: ${imei}, Battery: ${rand(1,6)}, GSM: ${rand(1,5)}, TermInfo: ${randomHex(8)}, Serial: ${serial}`
    );

    log(`Sent response: ${randomHex(20)}`);

    serial++;
}

function locationPacket() {

    const imei = randomIMEI();

    log(`Received: ${randomHex(80)}`);

    log(`serial ${serial}`);

    log(`Processing protocol: 0x22 `);

    log(
        `✅ Location - IMEI: ${imei}, Lat: ${randomLat()}, Lon: ${randomLon()}, Speed: ${rand(0,120)}, Course: ${rand(1000,6000)}, Serial: ${serial}`
    );

    serial++;
}

function unknownPacket() {

    log(`Received: ${randomHex(70)}`);

    log(`serial ${serial}`);

    log(`Processing protocol: 0x26 `);

    log(`⚠️ Unknown protocol: 0x26`);

    serial++;
}

function infoPacket() {

    log(`Received: ${randomHex(24)}`);

    log(`serial ${serial}`);

    log(`Processing protocol: 0x94 `);

    log(`ℹ️ Information transmission packet`);

    serial++;
}

function connectionError() {

    log(`Connection error: EOF`);
}

// ======================================================
// MAIN LOOP
// ======================================================

console.log("\nGPS Tracker Logger Started...\n");

setInterval(() => {

    const type = rand(1, 6);

    switch(type) {

        case 1:
            serverListening();
            break;

        case 2:
            loginPacket();
            break;

        case 3:
            heartbeatPacket();
            break;

        case 4:
            locationPacket();
            break;

        case 5:
            unknownPacket();
            break;

        case 6:
            infoPacket();
            break;
    }

    // Random connection errors
    if (Math.random() < 0.15) {
        connectionError();
    }


}, 2000);
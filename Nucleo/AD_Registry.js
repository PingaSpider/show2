const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const https = require('https');

const FILENAME = path.join(__dirname, 'data', 'drones_registry.json');

// Leer los archivos de certificado
const privateKey = fs.readFileSync('private.key', 'utf8');
const certificate = fs.readFileSync('certificate.crt', 'utf8');


const credentials = {
    key: privateKey,
    cert: certificate
};

const express = require('express');
const app = express();

app.use(express.json());  // Middleware para parsear JSON.


// Iniciar el servidor
const httpsServer = https.createServer(credentials, app);
httpsServer.listen(443, () => {
    console.log('HTTPS Server running on port 443');

    //Vaciar el archivo de drones
    fs.writeFileSync(FILENAME, JSON.stringify([], null, 2));
    //Sacar por consola el archivo vacío
    console.log("Archivo de drones vacío:", FILENAME);
});

app.get('/', (req, res) => {
    res.send('Hello HTTPS with Self-Signed Certificate!');
});


const loadDrones = () => {
    try {
        const data = fs.readFileSync(FILENAME, 'utf8');
        return JSON.parse(data);
    } catch (err) {
        console.error("Error loading the drone file:", err);
        return [];
    }
};

const saveDrones = (drones) => {
    try {
        // Guardar los drones en el archivo 
        //si el dron ya está registrado, se actualiza el token y la fecha de expiración
        fs.writeFileSync(FILENAME, JSON.stringify(drones, null, 2));
        //Sacar por consola el drone registrado
        console.log("Dron registrado:", drones);
        return true;
    } catch (err) {
        console.error("Error saving the drone file:", err);
        return false;
    }
};

const getUniqueToken = () => {
    return crypto.randomBytes(16).toString('hex');
};

app.post('/drones/register', (req, res) => {
    const { id } = req.body;
    let drones = loadDrones();
    let index = drones.findIndex(d => d.id === id);

    // Si el dron no está registrado, se genera un token y se guarda en el archivo.
    if (index === -1 || drones.length === 0) {
        const newToken = getUniqueToken();
        const timestamp = Date.now();
        const expiration = timestamp + 20000;
        //formato json para guardar en el archivo
        dron = {"id": id, "token": newToken, "timestamp": timestamp, "expiration": expiration};
        drones.push(dron);
        if (saveDrones(drones)) {
            res.status(201).json({ message: "Dron registrado con exito", token: newToken });
        } else {
            res.status(500).json({ message: "Error al guardar el dron" });
        }
    }
    else {
        dron = drones[index];
        //Es un json por lo que se puede acceder a los valores de la clave
        //Si el dron ya está registrado y no ha expirado el token, se actualiza el token y la fecha de expiración
        if (dron["expiration"] < Date.now()) {
            dron["token"] = hashToken(getUniqueToken());
            dron["timestamp"] = Date.now();
            dron["expiration"] = (dron.timestamp + 20000);
            drones[index] = dron;
            if (saveDrones(drones)) {
                res.status(201).json({ message: "Token renovado con éxito", token: dron.token });
            } else {
                res.status(500).json({ message: "Error al actualizar el token del dron" });
            }
        }else{
            res.status(202).json({ message: "Dron ya registrado", token: dron.token });
        }
    }
});

// Función para crear un hash SHA-256 de un token
function hashToken(token) {
    return crypto.createHash('sha256').update(token).digest('hex');
}

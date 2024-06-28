const express = require('express');
const bodyParser = require('body-parser');
const app = express();
const path = require('path');

const PORT = process.env.PORT || 5005;

let mapData = '';  // Cambiado para almacenar HTML del mapa
let logData = [];
// Cambiado para almacenar json de drones
let droneData = [];
let messageEngine = [];  // Cambiado para almacenar HTML de los logs
let confirmedData = '';  // Cambiado para almacenar HTML de los drones confirmados


app.use(bodyParser.json());  // Para parsear body de tipo JSON
app.use(express.static(path.join(__dirname, '/')));

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});


app.post('/map', (req, res) => {
    // Asumimos que el cuerpo de la solicitud ya es HTML válido
    mapData = req.body.mapHtml;
    res.status(200).send('Map data received');
});

app.get('/get_map', (req, res) => {
    if (mapData) {
        res.send(mapData);
    } else {
        res.status(404).send('No map data available');
    }
});

app.post('/drones', (req, res) => {
    if(droneData.length > 2){
        // Si hay más de 10 mensajes, eliminar el más antiguo
        droneData.shift();
        droneData.push(req.body);
    }else{
        droneData.push(req.body);
    
    }
    res.status(200).send('Drone data received');
});

//get para que el script saque las actualizaciones de drones
app.get('/get_drones', (req, res) => {
    if (!droneData) {
        res.status(404).send('No drone data available');
    } else {
        res.send(droneData);
        res.status(200).send('Drone data sent');
    }
});

//post para que el servidor reciba la información de auditoria de seguridad
app.post('/audit', (req,res) => {
    if(logData.length > 2){
        // Si hay más de 10 mensajes, eliminar el más antiguo
        logData.shift();
        logData.push(req.body);
    }else{
        logData.push(req.body);
    }
    res.status(200).send('Audit data received');
});

//get para que el script saque las actualizaciones de auditoria de seguridad
app.get('/get_audit', (req,res) => {
    if(logData == undefined){
        res.status(404).send('No audit data available');
    }
    else{
        res.send(logData);
        res.status(200).send('Audit data sent');
    }
});

//post para que el servidor reciba la información del engine
app.post('/engine', (req,res) => {
    if(messageEngine.length > 3){
        // Si hay más de 10 mensajes, eliminar el más antiguo
        messageEngine.shift();
        messageEngine.push(req.body.message);
    }
    else{
        messageEngine.push(req.body.message);
    }
    res.status(200).send('Engine data received');
});

//get para que el script saque las actualizaciones del engine
app.get('/get_engine', (req,res) => {
    if(messageEngine == undefined){
        res.status(404).send('No engine data available');
    }
    else{
        res.send(messageEngine);
        res.status(200).send('Engine data sent');
    }
});


//post para que el servidor reciba la información de los drones confirmados
app.post('/confirmed', (req,res) => {
    // Asumimos que el cuerpo de la solicitud ya es HTML válido
    confirmedData = req.body.message;
    res.status(200).send('Confirmed data received');
});

//get para que el script saque las actualizaciones de los drones confirmados
app.get('/get_confirmed', (req,res) => {
    if(confirmedData){
        res.send(confirmedData);
    }
    else{
        res.status(404).send('No confirmed data available');
    }
});


// Otros endpoints sin cambios...

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});

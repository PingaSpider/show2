//LISTO
// Event Listener para el DOM que carga el mapa y lo actualiza cada 1 segundos
document.addEventListener('DOMContentLoaded', function() {
    const mapContainer = document.getElementById('map');

    // Función para cargar el mapa
    function loadMap() {
        fetch('/get_map')
            .then(response => {
                if (response.ok) {
                    return response.text();
                } else {
                    throw new Error('Map data not available');
                }
            })
            .then(mapData => {
                mapContainer.innerHTML = mapData;
            })
            .catch(error => {
                console.error(error);
            });
    }

    // Cargar el mapa al cargar la página sino hay mapa enviar un mensaje de error
    if (mapContainer) {
        loadMap();
    } else {
        console.error('Map container not found');
    }

    //Llama a la función loadMap cada 3 segundos
    setInterval(loadMap, 1000);
});

//LISTO
// Event Listener para el DOM que carga los logs del engine y los actualiza cada 1 segundos
document.addEventListener('DOMContentLoaded', function() {
    const logContainer = document.getElementById('messages');

    function loadLogs() {
        fetch('/get_engine')
            .then(response => {
                if (response.ok) {
                    return response.json();  // Cambio aquí para asegurar que tratamos la respuesta como JSON
                } else {
                    throw new Error('Log data not available');
                }
            })
            .then(data => {
                
                if (data.length === 0) {
                    messageElement.textContent = 'No logs available';
                    logContainer.appendChild(messageElement);
                } else {
                    logContainer.innerHTML = '';  // Cambio aquí para limpiar el contenedor antes de agregar los nuevos logs
                    data.forEach(log => {
                        // Cambio aquí para limpiar el contenedor antes de agregar los nuevos logs
                        const messageElement = document.createElement('p');
                        // Asegurándose de que log es un string o accediendo a la propiedad adecuada
                        messageElement.textContent = log // Modifica esto según la estructura de tus logs
                        logContainer.appendChild(messageElement);
                    });
                }
            })
            .catch(error => {
                console.error(error);
            });
    }

    if (logContainer) {
        loadLogs();// Intervalo cambiado a 3 segundos para coincidir con el comentario
    } else {
        console.error('Log container not found');
    }

    setInterval(loadLogs, 500); // Cambio aquí para que se actualice cada 1 segundo
});

//LISTO
document.addEventListener('DOMContentLoaded', function() {
    const auditContainer = document.getElementById('audit');

    function loadAudits() {
        fetch('/get_audit')
            .then(response => {
                if (response.ok) {
                    return response.json();  // Cambio para manejar la respuesta como JSON
                } else {
                    throw new Error('Audit data not available');
                }
            })
            .then(audits => {
                auditContainer.innerHTML = '';  // Limpiar el contenedor antes de agregar nuevos elementos
                audits.forEach(audit => {
                    const auditElement = document.createElement('p');
                    auditElement.textContent = `Fecha y hora: ${audit.fecha_hora}, IP local: ${audit.ip_local}, IP origen: ${audit.ip_origen}, Evento: ${audit.evento}, Descripción: ${audit.descripcion}`;
                    auditContainer.appendChild(auditElement);
                });
            })
            .catch(error => {
                console.error(error);
                auditContainer.textContent = 'Failed to load audit data'; // Manejo de error en el contenedor
            });
    }

    loadAudits();
    setInterval(loadAudits, 1000);  // Refrescar los datos cada 3 segundos
});

//LISTO
// Event Listener para el DOM que carga los los drones confirmados y los actualiza cada 1 segundos
document.addEventListener('DOMContentLoaded', function() {
    const confirmedContainer = document.getElementById('confirm-section');

    // Función para cargar los drones confirmados
    function loadConfirmed() {
        fetch('/get_confirmed')
            .then(response => {
                if (response.ok) {
                    return response.text();
                } else {
                    response.status(404).send('No confirmed drones available');
                }
            })
            .then(confirmedData => {
                confirmedContainer.innerHTML = confirmedData;
            })
            .catch(error => {
                console.error(error);
            });
    }

    // Cargar los drones confirmados al cargar la página sino hay drones confirmados enviar un mensaje de error
    if (confirmedContainer) {
        loadConfirmed();
    } else {
        console.error('Confirmed container not found');
    }

    //Llama a la función loadConfirmed cada 3 segundos
    setInterval(loadConfirmed, 2000);
});


document.addEventListener('DOMContentLoaded', function() {
    const droneContainer = document.getElementById('drones');

    function loadDrones() {
        fetch('/get_drones')
            .then(response => {
                if (response.ok) {
                    return response.json();
                } else {
                    throw new Error('Drone data not available');
                }
            })
            .then(droneData => {
                droneContainer.innerHTML = '';// Limpiar el contenedor antes de agregar nuevos elementos
                
                droneData.forEach(drone => {
                        const droneElement = document.createElement('p');
                        droneElement.textContent = `ID_DRON: ${drone.ID_DRON},
                            Latitud: ${drone.COORDENADA_X_ACTUAL},
                            Longitud: ${drone.COORDENADA_Y_ACTUAL},
                            Altitud: ${drone.ESTADO_ACTUAL}
                        `;
                        droneContainer.appendChild(droneElement);
                    });
            })
            .catch(error => {
                console.error('Error loading drones:', error);
                droneContainer.innerHTML = '<p>Error loading drones. Please try again later.</p>';
            });
    }
    
    if (droneContainer) {
        loadDrones();
        setInterval(loadDrones, 1000); // Considera ajustar este intervalo según sea necesario
    } else {
        console.error('Drone container not found');
    }
});

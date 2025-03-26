mapboxgl.accessToken = 'pk.eyJ1IjoieWRhaTExMTIiLCJhIjoiY2x6ajE1bTRwMG4yZzJxcThleWoxMXJ1aiJ9.aBTNSgDeUDCJBkCpDEvopg';

document.addEventListener('DOMContentLoaded', function() {
    const map = new mapboxgl.Map({
        container: 'map', // id of the element where the map will be injected
        style: 'mapbox://styles/mapbox/dark-v10', // changed base map style
        center: [0, 0], // updated to world view
        zoom: 2         // updated to world view
    });

    // Define flag to stop zooming
    let stopZoom = false;
    map.on('click', () => {
        stopZoom = true;
    });

    // Variable to store the currently open popup
    let currentPopup = null;

    map.on('load', function () {

        // Fetch GeoJSON data and add markers
        fetch("geojson_output/locations_JackKerouac-On the Road(1976).geojson")
            .then(response => {
                if (!response.ok) {
                    throw new Error("Network response was not ok: " + response.statusText);
                }
                return response.json();
            })
            .then(geojson => {
                console.log("GeoJSON data loaded:", geojson);

                // Group features by coordinates
                const groupedFeatures = {};
                geojson.features.forEach(feature => {
                    const coordinates = feature.geometry.coordinates.join(','); // Use a string key
                    if (!groupedFeatures[coordinates]) {
                        groupedFeatures[coordinates] = {
                            coordinates: feature.geometry.coordinates,
                            properties: []
                        };
                    }
                    groupedFeatures[coordinates].properties.push(feature.properties);
                });

                // Convert groupedFeatures to an array for easier processing
                const featureArray = Object.values(groupedFeatures);

                // Calculate bounding box
                let bounds = new mapboxgl.LngLatBounds();
                featureArray.forEach(groupedFeature => {
                    bounds.extend(groupedFeature.coordinates);
                });

                // Fit map to bounds
                map.fitBounds(bounds, {
                    padding: 50 // Add some padding around the markers
                });
                
                // Initialize drawn line coordinates and add source & layer for the line
                const drawnLineCoords = [];
                let lineData = {
                    type: 'Feature',
                    properties: {},
                    geometry: {
                        type: 'LineString',
                        coordinates: drawnLineCoords
                    }
                };
                map.addSource('route', {
                    type: 'geojson',
                    data: lineData
                });
                map.addLayer({
                    id: 'route',
                    type: 'line',
                    source: 'route',
                    layout: {
                        'line-join': 'round',
                        'line-cap': 'round'
                    },
                    paint: {
                        'line-color': '#888',
                        'line-width': 0.25
                    }
                });

                // Animate markers one at a time and zoom into each location
                function animateMarkers(index) {
                    if (index >= featureArray.length) return;
                    const { coordinates, properties } = featureArray[index];
                    
                    // Combine contexts and presences
                    const uniqueContexts = [];
                    properties.forEach(prop => {
                        const context = prop.context || "No context available";
                        if (!uniqueContexts.includes(context)) {
                            uniqueContexts.push(context);
                        }
                    });
                    const contexts = uniqueContexts.join("<hr>");
                    
                    // Highlight occurrences of the name in the context text
                    const highlightedContexts = contexts.replace(new RegExp(properties[0].LocationName, 'g'),
                        '<span style="background-color: yellow; font-weight: bold;">' + properties[0].LocationName + '</span>');
                    
                    const uniquePresences = [];
                    properties.forEach(prop => {
                        const presence = prop.Presence || "No Presence specified";
                        if (!uniquePresences.includes(presence)) {
                            uniquePresences.push(presence);
                        }
                    });
                    const presences = uniquePresences.join("<hr>");
                    const locations = properties.map(prop => prop.LocationName || "LocationName").join("<hr>");
                    
                    let presence = properties[0].Presence || "Presence not specified";

                    // Create popup using highlightedContexts instead of contexts
                    const popup = new mapboxgl.Popup({ offset: 15, closeOnClick: false, anchor: 'left' }).setHTML(
                        `<div style="max-height: 500px; width: 700px; overflow-y: auto;">
                            <h2 style="position: sticky; top: 0; background-color: white; z-index: 1;">${properties[0].LocationName}</h2>
                            <p>${highlightedContexts || "No context available"}</p>
                        </div>`
                    );
                    
                    const el = document.createElement('img');
                    el.src = 'assets/marker_logo-01.png';
                    el.style.width = '30px'; // Marker image width
                    el.style.height = '30px'; // Marker image height
                    
                    const marker = new mapboxgl.Marker(el, { anchor: 'bottom' })
                        .setLngLat(coordinates)
                        .addTo(map);
                    
                    // Show popup immediately as marker appears
                    if (currentPopup) {
                        currentPopup.remove();
                    }
                    popup.setLngLat(coordinates);
                    popup.addTo(map);
                    currentPopup = popup;
                    
                    // Update line drawing as marker appears
                    drawnLineCoords.push(coordinates);
                    map.getSource('route').setData(lineData);
                    
                    // Replace previous event listeners for popup:
                    let hoverTimer;
                    el.addEventListener('mouseenter', () => {
                        hoverTimer = setTimeout(() => {
                            // Close the current popup if it exists
                            if (currentPopup) {
                                currentPopup.remove();
                            }
                            popup.setLngLat(coordinates);
                            popup.addTo(map);
                            currentPopup = popup; // Set the current popup
                            map.panTo(coordinates, { duration: 1000 }); // increased duration for smoother panning
                        }, 0);
                    });
                    el.addEventListener('mouseleave', () => {
                        clearTimeout(hoverTimer);
                        // Do not remove popup once it is shown.
                    });
                    
                    // Only zoom if stopZoom flag is false
                    if (!stopZoom) {
                        // Enlarge current marker when hovering over and the popup shows up
                        el.style.transition = 'width 0.3s, height 0.3s';
                        el.style.width = '100px';
                        el.style.height = '100px';
                        map.flyTo({
                            center: coordinates,
                            zoom: 12,      // reduced zoom level for less drastic zoom in
                            speed: 0.5,    // slower animation speed
                            easing: t => t // linear easing for smoother movement
                        });
                        // Revert marker size after zoom animation completes
                        map.once('moveend', () => {
                            el.style.width = '30px';
                            el.style.height = '30px';
                        });
                    }
                    
                    // Show next marker after a short delay (adjust delay as needed)
                    setTimeout(() => animateMarkers(index + 1), 1500);
                }
                animateMarkers(0);
            })
            .catch(error => console.error("Error loading GeoJSON:", error));
    });
});
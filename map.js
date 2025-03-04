// Initialize Mapbox
mapboxgl.accessToken = 'pk.eyJ1IjoieWRhaTExMTIiLCJhIjoiY2x6ajE1bTRwMG4yZzJxcThleWoxMXJ1aiJ9.aBTNSgDeUDCJBkCpDEvopg';

document.addEventListener('DOMContentLoaded', function() {
    const map = new mapboxgl.Map({
        container: 'map', // id of the element where the map will be injected
        style: 'mapbox://styles/mapbox/streets-v11',
        center: [-71.0589, 42.3601], // Boston, MA
        zoom: 12
    });

    // Once the map loads, apply the grayscale filter to its canvas only,
    // leaving externally added markers (in interface.html) unaffected.
    map.on('load', function () {
        map.getCanvas().style.filter = 'grayscale(100%)';

        // Fetch GeoJSON data and add markers
        fetch("geojson_output/locations_henry-david-thoreau_walden.geojson")
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

                // Create markers for each group of features
                featureArray.forEach(groupedFeature => {
                    const { coordinates, properties } = groupedFeature;
                    console.log("Coordinates:", coordinates);

                    // Combine all contexts and presences into a single string
                    const uniqueContexts = [];
                    properties.forEach(prop => {
                        const context = prop.context || "No context available";
                        if (!uniqueContexts.includes(context)) {
                            uniqueContexts.push(context);
                        }
                    });
                    const contexts = uniqueContexts.join("<hr>");

                    const uniquePresences = [];
                    properties.forEach(prop => {
                        const presence = prop.Presence || "No Presence specified";
                        if (!uniquePresences.includes(presence)){
                            uniquePresences.push(presence);
                        }
                    });
                    const presences = uniquePresences.join("<hr>");

                    const locations = properties.map(prop => prop.name || "name").join("<hr>");

                    // Determine marker color based on presence (using the first presence for simplicity)
                    let presence = properties[0].Presence || "Presence not specified";
                    let markerColor = 'lightblue'; // Default color
                    if (presence.includes("Likely physically present")) {
                        markerColor = 'rgba(29, 98, 28, 0.41)'; // Green
                    } else if (presence.includes("Physically present")) {
                        markerColor = 'rgb(29, 98, 28)'; // Dark Green
                    } else if (presence.includes("Mentally present")) {
                        markerColor = 'rgb(29, 98, 28)'; // Pink
                    } else if (presence.includes("Unclear")) {
                        markerColor = 'rgba(4, 255, 0, 0.35)'; // Pink
                    } else {
                        markerColor = 'rgba(4, 255, 0, 0.35)'; // Default color
                    }

                    // Create a popup with all contexts and presences
                    const popup = new mapboxgl.Popup({ offset: 25 }).setHTML(
                        `<div style="max-height: 200px; max-width: 500px; overflow-y: auto;">
                            <h2 style="position: sticky; top: 0; background-color: white; z-index: 1;">${properties[0].name}</h2>
                            <p>${properties[0].context || "No context available"}</p>
                            <p>Presence: ${properties[0].Presence || "Presence not specified"}</p>
                            <hr>
                            <p>${contexts}</p>
                            <p>Presence: ${presences}</p>
                        </div>`
                    );

                    // Create a custom marker element
                    const el = document.createElement('div');
                    el.style.width = '10px';
                    el.style.height = '10px';
                    el.style.backgroundColor = markerColor;
                    el.style.borderRadius = '50%';

                    // Add the custom marker to the map
                    const marker = new mapboxgl.Marker(el)
                        .setLngLat(coordinates)
                        .setPopup(popup)
                        .addTo(map);
                    console.log("Marker created:", marker);
                });

                // Prepare line data
                const lineCoordinates = featureArray.map(feature => feature.coordinates);
                let lineData = {
                    type: 'Feature',
                    properties: {},
                    geometry: {
                        type: 'LineString',
                        coordinates: []
                    }
                };

                // Add source and layer for the line
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

                // Animate the line drawing
                let i = 0;
                function animateLine() {
                    // Check if the map is zoomed out enough
                    if (map.getZoom() < 5) { // Adjust the zoom level as needed
                        if (i < lineCoordinates.length) {
                            lineData.geometry.coordinates = lineCoordinates.slice(0, i + 1);
                            map.getSource('route').setData(lineData);
                            i++;
                            setTimeout(animateLine, 100); // Adjust the timeout for animation speed
                        }
                    } else {
                        // If not zoomed out enough, wait and check again
                        setTimeout(animateLine, 1000); // Check every 1 second
                    }
                }
                animateLine();
            })
            .catch(error => console.error("Error loading GeoJSON:", error));
    });
});
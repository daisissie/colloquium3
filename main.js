// Initialize Mapbox
mapboxgl.accessToken = 'pk.eyJ1IjoieWRhaTExMTIiLCJhIjoiY2x6ajE1bTRwMG4yZzJxcThleWoxMXJ1aiJ9.aBTNSgDeUDCJBkCpDEvopg';
const map = new mapboxgl.Map({
    container: 'map', // id of the element where the map will be injected
    style: 'mapbox://styles/mapbox/streets-v11',
    center: [0, 0], // Set initial center coordinates
    zoom: 2 // Set initial zoom level
});

// Load and display GeoJSON data
map.on('load', function () {
    fetch('/prototying_tuvalu/output/tuvalu1_locations.geojson')
        .then(response => response.json())
        .then(data => {
            map.addSource('walden_locations', {
                type: 'geojson',
                data: data
            });

            map.addLayer({
                id: 'walden_locations',
                type: 'circle',
                source: 'walden_locations',
                paint: {
                    'circle-radius': 6,
                    'circle-color': '#B42222'
                }
            });

            map.addLayer({
                id: 'walden_locations_labels',
                type: 'symbol',
                source: 'walden_locations',
                layout: {
                    'text-field': ['get', 'Location'],
                    'text-font': ['Open Sans Semibold', 'Arial Unicode MS Bold'],
                    'text-offset': [0, 0.6],
                    'text-anchor': 'top'
                }
            });

            // Add popups with location information
            data.features.forEach(function (feature) {
                const coordinates = feature.geometry.coordinates.slice();
                const name = feature.properties.name;
                const context = feature.properties.context; // new: get context

                new mapboxgl.Marker()
                    .setLngLat(coordinates)
                    .setPopup(
                        new mapboxgl.Popup().setHTML(`<h3>${name}</h3><p>${context}</p>`)
                    )
                    .addTo(map);
            });
        })
        .catch(error => console.error('Error loading GeoJSON data:', error));
});
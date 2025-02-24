// Initialize Mapbox
mapboxgl.accessToken = 'pk.eyJ1IjoieWRhaTExMTIiLCJhIjoiY2x6ajE1bTRwMG4yZzJxcThleWoxMXJ1aiJ9.aBTNSgDeUDCJBkCpDEvopg';
const map = new mapboxgl.Map({
    container: 'map', // id of the element where the map will be injected
    style: 'mapbox://styles/mapbox/streets-v11',
    center: [0, 0], // Set initial center coordinates
    zoom: 2 // Set initial zoom level
});

// Once the map loads, apply the grayscale filter to its canvas only,
// leaving externally added markers (in interface.html) unaffected.
map.on('load', function () {
    map.getCanvas().style.filter = 'grayscale(100%)';
});
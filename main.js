// Initialize Mapbox
mapboxgl.accessToken = 'pk.eyJ1IjoieWRhaTExMTIiLCJhIjoiY2x6ajE1bTRwMG4yZzJxcThleWoxMXJ1aiJ9.aBTNSgDeUDCJBkCpDEvopg';
const map = new mapboxgl.Map({
    container: 'map', // id of the element where the map will be injected
    style: 'mapbox://styles/mapbox/streets-v11',
    zoom: 8
});

// Add a marker at the specified coordinates
new mapboxgl.Marker()
    .setLngLat([150.644, -34.397])
    .setPopup(new mapboxgl.Popup().setText('Lat: -34.397, Lng: 150.644'))
    .addTo(map);

new mapboxgl.Marker()
    .setLngLat([151.2093, -33.8688]) // Sydney coordinates
    .setPopup(new mapboxgl.Popup().setText('Lat: -33.8688, Lng: 151.2093'))
    .addTo(map);

new mapboxgl.Marker()
    .setLngLat([144.9631, -37.8136]) // Melbourne coordinates
    .setPopup(new mapboxgl.Popup().setText('Lat: -37.8136, Lng: 144.9631'))
    .addTo(map);

new mapboxgl.Marker()
    .setLngLat([153.0281, -27.4679]) // Brisbane coordinates
    .setPopup(new mapboxgl.Popup().setText('Lat: -27.4679, Lng: 153.0281'))
    .addTo(map);
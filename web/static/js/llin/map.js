var stats = null;
$.get('/api/v1/districtstats', {field: 'color'},
        function(data){
    stats = data;
});
var coverage = null;
$.get('/api/v1/districtstats', {field: 'coverage'},
        function(data){
    coverage = data;
});

var layer = new ol.layer.Tile({
	source: new ol.source.OSM()
});
// create a vector source that loads a GeoJSON file
var vectorSource = new ol.source.Vector({
	projection: 'EPSG:3857',
	url: '/static/geojson/uganda.geojson',
	format: new ol.format.GeoJSON()
});

// a vector layer to render the source
var district = '';
var dobj;
var vectorLayer = new ol.layer.Vector({
	source: vectorSource,
	style: function(feature, res){
        var p = JSON.parse(stats);
        var district = feature.get("DISTRICT");
        var col = p[district];
        return new ol.style.Style({
            stroke: new ol.style.Stroke({
                color: 'rgba(112, 128, 144, 0.5)',
                width: 1
            }),

            fill: new ol.style.Fill({
                color: col,
                opacity: 0.1
            })
		});
    }

});

// var center = ol.proj.transform([0, 0], 'EPSG:4326', 'EPSG:3857');
// var center = ol.proj.transform([32.582520, 0.347596], 'EPSG:4326', 'EPSG:3857');
/*Amolator seems to be more middle like*/
var center = ol.proj.transform([32.8250, 1.6350], 'EPSG:4326', 'EPSG:3857');

var view = new ol.View({
	center: center,
	zoom: 7
});
/*
var overlay = new ol.Overlay({
    element: document.getElementById('overlay')
});
*/

// the vector layer gets added like a raster layer
var map = new ol.Map({
	target: 'map',
	layers: [layer, vectorLayer],
	view: view
});

map.on('pointermove', function(event){
    map.forEachFeatureAtPixel(event.pixel, function (feature, layer) {
        district = feature.get("DISTRICT");
        var p = JSON.parse(coverage);
        $('#overlay').html(p[district]);
    });
});

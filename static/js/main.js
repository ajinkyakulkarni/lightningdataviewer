window['_fs_ready'] = function () {
    var sessionUrl = FS.getCurrentSessionURL();
    var sessionUrlAtCurrentTime = FS.getCurrentSessionURL(true);
};

let viewer = false;
let date = "2019-03-04";
let dateFormat = "YYYY-MM-DD h:mm:ss";
let timerId = false;
let lightningImages = [];
let chart = false;
let lightningEvents = [];
let currentIndex = -1;
let uid = false;

/*
    jQuery REST call get logged in user's info
 */
jQuery.getJSON("/user", function (data) {
    if (!jQuery.isEmptyObject(data)) {
        uid = data.uid
    }

    if (uid !== false && uid !== undefined) {
        FS.identify(uid);
    }

});

/*
    Create jQuery UI dialog box
 */
let dialogBox = jQuery("#dialog-form").dialog({
    autoOpen: false,
    height: 400,
    width: 400,
    modal: true,
    buttons: {

        Submit: function () {
            let issueType = jQuery("input[type=radio][name=radio]:checked").val();
            let issue_body = jQuery("#issue-body").val();
            let issue_title = jQuery("#issue-title").val();


            jQuery.ajax({
                url: "/issue",
                dataType: 'json',
                type: 'post',
                contentType: 'application/json',
                data: JSON.stringify({
                    "issue_title": issue_title,
                    "issue_body": issue_body,
                    "issue_type": issueType
                }),
                processData: false,
                success: function (data, textStatus, jQxhr) {
                    alert("Your feedback was recorded successfully");
                },
                error: function (jqXhr, textStatus, errorThrown) {
                    alert("There was error posting your feedback.");
                }
            });


        },
        Cancel: function () {
            dialogBox.dialog("close");
        }
    },
    close: function () {


    }
});

/*
   jQuery click listener to show the dialog box to file an issue.
   If user is not logged into Github then page would be redirected to Github login page first
 */
jQuery('#report-bug').click(function (e) {
    e.preventDefault();

    if (uid === false) {
        alert("You will need to first login using Github. You will be now redirected to Github to login. After login, you will be able to report bug or feature.");
        window.location = "/login";
    } else {
        dialogBox.dialog("open");
    }

});

/*
    Create daily MODIS cloud provider
 */
function createDailyProvider(time) {

    let provider = new Cesium.WebMapTileServiceImageryProvider({
        url: 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/wmts.cgi?time=' + time,
        layer: 'MODIS_Terra_CorrectedReflectance_TrueColor',
        style: '',
        format: 'image/jpeg',
        tileMatrixSetID: 'EPSG4326_250m',
        maximumLevel: 8,
        tileWidth: 256,
        tileHeight: 256,
        tilingScheme: gibs.GeographicTilingScheme()
    });

    return provider;
}

/*
    Create toggle buttons
 */
function enableToggles() {

    jQuery('#toggle-clouds').change(function () {

        let checked = jQuery(this).prop('checked');
        if (checked) {
            dailyLayer = viewer.imageryLayers.addImageryProvider(createDailyProvider(moment.utc(date).format("YYYY-MM-DD")));

        } else {
            viewer.scene.imageryLayers.remove(dailyLayer);

        }


    });

    jQuery('#toggle-animation').change(function () {

        let checked = jQuery(this).prop('checked');
        if (checked) {
            playAnimation();

        } else {
            stopAnimation();
        }


    });

    jQuery('#toggle-2d').change(function () {

        let checked = jQuery(this).prop('checked');
        if (checked) {
            viewer.scene.mode = Cesium.SceneMode.SCENE3D;
        } else {
            viewer.scene.mode = Cesium.SceneMode.SCENE2D;
        }

    });


}

/*
    Stop/clear the animation
 */
function stopAnimation() {

    clearInterval(timerId);

    viewer.entities.removeAll();
    chart.xAxis[0].removePlotLine('plot-line');

    currentIndex = -1;

    jQuery.each(lightningEvents, function (index, currentEvent) {
        let entity = viewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees(currentEvent.flash_longitude, currentEvent.flash_latitude),
            show: true,
            point: {
                color: Cesium.Color.RED,
                pixelSize: 10,
                glowPower: currentEvent.flash_observe_time
            }
        });
    });
}

/*
    Start the animation
 */
function playAnimation() {

    viewer.entities.removeAll();

    timerId = setInterval(() => {

        jQuery(lightningImages).each(function (index, item) {
            viewer.entities.remove(item);
        });


        do {


            currentIndex++;
            let currentEvent = lightningEvents[currentIndex];
            if (currentEvent === undefined) {
                viewer.entities.removeAll();
                chart.xAxis[0].removePlotLine('plot-line');
                currentIndex = -1;
                return;
            }

            chart.xAxis[0].removePlotLine('plot-line');
            chart.xAxis[0].addPlotLine({
                color: 'red',
                dashStyle: 'solid',
                value: currentEvent.flash_timestamp,
                width: 2,
                id: 'plot-line'
            });

            let entity = viewer.entities.add({
                position: Cesium.Cartesian3.fromDegrees(currentEvent.flash_longitude, currentEvent.flash_latitude),
                show: true,
                point: {
                    color: Cesium.Color.RED,
                    pixelSize: 10,
                    glowPower: currentEvent.flash_observe_time
                }
            });
            let lightningImage = viewer.entities.add({
                position: Cesium.Cartesian3.fromDegrees(currentEvent.flash_longitude, currentEvent.flash_latitude),
                show: true,
                billboard: {
                    image: 'static/images/lightning4.png',
                    scaleByDistance: new Cesium.NearFarScalar(1.5e2, 2.0, 1.5e7, 0.5),
                    translucencyByDistance: new Cesium.NearFarScalar(1.5e2, 2.0, 1.5e7, 0.5)
                }

            });
            lightningImages.push(lightningImage);


            viewer.clock.currentTime = Cesium.JulianDate.fromIso8601(moment.utc(currentEvent.flash_timestamp).toISOString());


        } while (lightningEvents[currentIndex + 1] !== undefined && lightningEvents[currentIndex + 1].flash_timestamp == lightningEvents[currentIndex].flash_timestamp);


    }, 10);
}

/*
    Create Highchart scatter plot
 */
function createChart(data) {

    Highcharts.setOptions({
        time: {
            useUTC: true
        }
    });

    chart = Highcharts.chart('chartContainer', {
        chart: {
            type: 'scatter',
            zoomType: 'xy'
        },
        title: {
            text: 'Flash Start Time vs Flash Observe Time of ' + data.length + ' Individuals Flashes'
        },
        subtitle: {
            text: 'Source: GHRC DAAC'
        },
        xAxis: {
            type: 'datetime',
            title: {
                enabled: true,
                text: 'Flash Start Time'
            },
            startOnTick: true,
            endOnTick: true,
            showLastLabel: true
        },
        yAxis: {
            title: {
                text: 'Flash Observe Time'
            }
        },
        legend: {
            layout: 'vertical',
            align: 'left',
            verticalAlign: 'top',
            x: 100,
            y: 70,
            floating: true,
            backgroundColor: (Highcharts.theme && Highcharts.theme.legendBackgroundColor) || '#FFFFFF',
            borderWidth: 1,
            enabled: false
        },
        plotOptions: {
            scatter: {
                marker: {
                    radius: 3,
                    states: {
                        hover: {
                            enabled: true,
                            lineColor: 'rgb(100,100,100)'
                        }
                    }
                },
                states: {
                    hover: {
                        marker: {
                            enabled: false
                        }
                    }
                },
                tooltip: {
                    headerFormat: '<b>{series.name}</b><br>',
                    pointFormatter: function () {
                        return "Time = " + moment.utc(this.x).format(dateFormat) + ", Observe Seconds = " + this.y;
                    }
                }
            }
        },
        series: [{
            name: 'Date: ' + date,
            color: 'rgba(223, 83, 83, .5)',
            data: data

        }]
    });


}

/*
    This function creates Cesium viewer object and sets default values
 */
function createViewer() {
    viewer = new Cesium.Viewer('cesiumContainer', {skyAtmosphere: false, baseLayerPicker: false});
    viewer.scene.mode = Cesium.SceneMode.SCENE2D;
    viewer.clock.currentTime = Cesium.JulianDate.fromIso8601("2019-03-04T00:00:00.000Z");
    viewer.timeline.zoomTo(Cesium.JulianDate.fromIso8601("2019-03-04T00:00:00.000Z"), Cesium.JulianDate.fromIso8601("2019-03-04T23:59:59.000Z"));

}

/*
    Call the data API endpoints to get lightning data points to plot on the map
 */
jQuery.getJSON("/data", function (data) {
    let items = [];

    jQuery.each(data, function (key, val) {

        let start_time = moment.utc(val.flash_start_time, dateFormat);

        let lightningEvent = {
            "flash_longitude": val.flash_longitude,
            "flash_latitude": val.flash_latitude,
            "flash_observe_time": Math.abs(parseFloat(val.flash_observe_time)),
            "flash_timestamp": start_time.valueOf()
        };

        lightningEvents.push(lightningEvent);
        items.push([start_time.valueOf(), Math.abs(parseFloat(val.flash_observe_time))]);

    });

    lightningEvents = _.sortBy(lightningEvents, function (o) {
        return new moment(o.flash_timestamp);
    });

    createViewer();
    createChart(items);
    playAnimation();
    enableToggles()

});
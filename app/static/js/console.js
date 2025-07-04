$(document).ready(function () {
    let engine_id = $("#engine_id").val();
    let engine_stopped = undefined;


    let data = new FormData();
    data.append("id", engine_id);

    $.ajax({
        url: '/train/engine-running',
        method: 'POST',
        data: data,
        contentType: false,
        cache: false,
        processData: false,
        success: function (response) {
            if (!response.stopped) {
                $('.dashboard-btns').addClass('d-none');
            } else {
                $('.dashboard-btns').removeClass('d-none');
            }

        },
        error: function (xhr, status, error) {
            console.error(error, "Task id not saved")
        }
    });




    const interval = 1000;
    let setupTimer = (el) => {
        let elapsed = parseInt($(el).attr("data-elapsed"));
        let timestamp = parseInt($(el).attr("data-started"));
        let now = moment();
        let start = moment.unix(timestamp);
        start = start.add(2, 'hours');
        let duration = moment.duration(now.diff(start)).add(elapsed, "seconds")


        $(el).html(moment.utc(duration.asMilliseconds()).format("HH:mm:ss"))
    }
    $(".time-left").each(function (i, el) {
        setupTimer(el)
        setInterval(() => {

            setupTimer(el)
        }, interval);
    });


    /// Training rounds and historic training data code

    function displayRounds(rounds) {
        if (Object.entries(rounds).length === 1) return;
        const container = $(".rounds-container");
        container.html("");

        $(".rounds").removeClass("d-none")

        Object.entries(rounds).map((round) => {
            container.append(`<button data-path="${round[0]}" class="ml-2 rounds-btn">${round[0]}</button>`)
        })
    }


    function readYamlFile(userId, engineId) {
        return $.ajax({
            url: `/train/graph_logs?user_id=${userId}&engine_id=${engineId}`,
            method: 'GET',
            dataType: 'json'
        });
    }

    readYamlFile(userId, engine_id)
        .then(data => {
            if (data) {
                displayRounds(data);
            }

        })
        .catch(error => console.error('Error:', error.statusText));


    $('.rounds-container').on('click', '.rounds-btn', function () {
        $(this).addClass('active-round').siblings().removeClass('active-round');
        const path = $(this).data('path');

        retrieveTrainingRound(path);
    });

    $('.dashboard-btns').on('click', '.full', function () {
        $(this).addClass('active-round').siblings().removeClass('active-round');

        retrieveFullTrainingData(engine_id);
    });




    let make_chart = (element, chart_data) => {
        let chart = new ApexCharts(element, {
            series: [{
                name: chart_data.y,
                data: Array.from(Array(250), (_, i) => [i, 0])
            }],
            chart: {
                id: chart_data.id,
                group: 'training',
                type: 'area',
                stacked: false,
                height: 400,
                zoom: {
                    type: 'x',
                    enabled: true,
                    autoScaleYaxis: true
                },
                toolbar: {
                    autoSelected: 'zoom'
                }
            },
            fill: {
                type: 'gradient',
                gradient: {
                    shadeIntensity: 1,
                    inverseColors: false,
                    opacityFrom: 0.5,
                    opacityTo: 0,
                    stops: [0, 90, 100]
                },
            },
            dataLabels: { enabled: false },
            yaxis: {
                title: { text: chart_data.y },
                labels: {
                    formatter: (val) => {
                        if (val == 0) return 0

                        if (chart_data.id != "train_learning_rate") {
                            if (val == 0) return 0
                            if (val % parseInt(val) == 0) return parseInt(val)
                            return val.toFixed(2)
                        } else {
                            return val.toExponential(2);
                        }
                    },

                    minWidth: 40
                },
                min: (chart_data.id == "valid_score") ? 0 : undefined,
                max: (chart_data.id == "valid_score") ? 60 : undefined
            },
            xaxis: {
                title: { text: chart_data.x },
                tickAmount: 10,
                labels: {
                    formatter: (val) => {
                        return val > 100 ? parseInt(val / 100) * 100 : Math.ceil(val);
                    }
                }
            },
            tooltip: {
                shared: true
            }
        });

        return chart;
    };

    const chart_metadata = {
        "train/train_batch_loss": { x: "Steps", y: "Batch loss", id: "train_batch_loss", last: 0 },
        "train/train_learning_rate": { x: "Steps", y: "Learning rate", id: "train_learning_rate", last: 0 },
        "valid/valid_ppl": { x: "Steps", y: "Batch loss", id: "valid_loss", last: 0 },
        "valid/valid_score": { x: "Steps", y: "Score", id: "valid_score", last: 0 }
    }

    let chart_series = {
        "train/train_batch_loss": [],
        "train/train_learning_rate": [],
        "valid/valid_ppl": [],
        "valid/valid_score": []
    }

    let charts = {}
    $(".training-chart").each(function (i, e) {
        let tag = $(this).attr("data-tag");
        let chart = make_chart(e, chart_metadata[tag])
        charts[tag] = chart;
        chart.render();
    });

    longpoll(5000, {
        url: `../graph_data`,
        method: "post",
        data: {
            tags: Object.keys(chart_metadata),
            id: engine_id
        }
    }, function (data) {
        $(".training-chart").each(function (i, e) {
            let tag = $(this).attr("data-tag");
            if (data) {
                let { stats, stopped } = data
                let tag_stats = stats[tag];
                if (tag_stats) {
                    let series = []
                    for (stat of tag_stats) {
                        series.push([stat.step, stat.value])
                    }

                    charts[tag].updateSeries([{ data: series }]);
                }
            }
        });

        // We don't keep longpolling if training is done
        if (data && data.stopped) return false
    }, true);

    let monitor_test = (task_id) => {
        $('.test-bleu-value').html("0.00");
        $('.test-btn').addClass('d-none');
        $('.test-animation').removeClass('done');
        $('.test-panel').removeClass('d-none');

        longpoll(5000, {
            url: '../test_status',
            method: 'POST',
            data: { task_id: task_id }
        }, (data) => {
            if (data.result == 200) {
                let score = parseFloat(data.test.bleu).toFixed(2);
                $('.test-bleu-value').html(score);
                $('.test-animation').addClass('done');
                return false;
            } else if (data.result == -2) {
                $('.test-btn').removeClass('d-none');
                $('.test-panel').addClass('d-none');
                return false;
            }
        });
    }

    $('.test-btn').on('click', function () {
        $.ajax({
            url: '../test',
            method: 'POST',
            data: { engine_id: engine_id }
        }).done(function (task_id) {
            monitor_test(task_id);
        })
    });



    /* Train status */
    longpoll(5000, {
        url: `../train_status`,
        method: "post",
        data: {
            id: engine_id
        }
    }, (data) => {
        if (engine_stopped != undefined && engine_stopped == false && data.stopped == true) {
            // This means the engine stopped while the console was open
            window.location.reload();
        }

        if (data.test_task_id) {
            monitor_test(data.test_task_id);
        } else if (data.test_score != undefined) {
            $('.test-bleu-value').html(data.test_score);
            $('.test-animation').addClass('done');
            $('.test-panel').removeClass('d-none');
        }

        if (data.stats && data.stats['epoch']) {
            $(".epoch-no").html(data.stats['epoch'])
        }

        if (data.power) {
            $(".gpu-power").html(data.power);
        }

        if (data.power_reference) {
            $(".power-reference").html("");
            for (power_ref of data.power_reference) {
                $(".power-reference").html($(".power-reference").html() + `${power_ref}<br />`)
            }
        }

        // We don't keep longpolling if training is done
        $.ajax({
            url: '../train_stats',
            method: 'post',
            data: { id: engine_id }
        }).done(function (data) {
            $(".time-container").html(data.data.time_elapsed);
            $(".score-container").html(data.data.score + " BLEU");
            $(".tps-container").html(data.data.tps);
            $(".ppl-container").html(data.data.ppl);
            $(".vocabulary-size-container").html(data.data.vocab_size);
            $(".beam-size-container").html(data.data.beam_size);
            $(".batch-size-container").html(data.data.batch_size);
            $(".validation-freq-container").html(data.data.val_freq);
            $(".patience-container").html(data.data.patience);
            $(".epochs-container").html(data.data.epochs);
        })

        engine_stopped = data.stopped

        return data.stopped ? false : true;
    }, true);

    /* Train log */
    let log_table = $(".log-table").DataTable({
        processing: true,
        serverSide: true,
        responsive: true,
        order: [[0, "desc"]],
        ajax: {
            url: "../log",
            method: "post",
            data: { engine_id: engine_id }
        },
        columnDefs: [{
            targets: [0, 1, 2, 3, 4],
            responsivePriority: 1
        }]
    });

    setInterval(() => {
        if (log_table.page() == 0 && !engine_stopped) {
            log_table.ajax.reload()
        }
    }, 5000);


    function retrieveTrainingRound(path) {
        $.ajax({
            url: `../historic_training_data`,
            method: "post",
            data: {
                tags: Object.keys(chart_metadata),
                engine_id: engine_id,
                graph_id: path
            }, success:
                function (data) {
                    $(".training-chart").each(function (i, e) {
                        let tag = $(this).attr("data-tag");
                        if (data) {
                            let { stats, stopped } = data
                            let tag_stats = stats[tag];
                            if (tag_stats) {
                                let series = []
                                for (stat of tag_stats) {
                                    series.push([stat.step, stat.value])
                                }

                                charts[tag].updateSeries([{ data: series }]);
                            }
                        }
                    });

                }
        });
    }



    function retrieveFullTrainingData(engine_id) {
        $.ajax({
            url: `../full_training_graph`,
            method: "post",
            data: {
                tags: Object.keys(chart_metadata),
                engine_id: engine_id,
            }, success:
                function (data) {
                    $(".training-chart").each(function (i, e) {
                        let tag = $(this).attr("data-tag");
                        if (data) {
                            let { stats, stopped } = data
                            let tag_stats = stats[tag];
                            if (tag_stats) {
                                let series = []
                                for (stat of tag_stats) {
                                    series.push([stat.step, stat.value])
                                }

                                charts[tag].updateSeries([{ data: series }]);
                            }
                        }
                    });

                }
        });
    }


});
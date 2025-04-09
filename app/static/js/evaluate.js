$(document).ready(function () {

  $(".evaluate-status").attr("data-status", "error");
  $(".evaluate-form").find("input").prop('disabled', false);
  $(".evaluate-form").find("input").removeClass("disabled-link");
  $(".evaluate-form").find("a").on('click');
  $(".evaluate-form").find("a").removeClass("disabled-link");

  let mt_filenames = [];
  let ht_filenames = [];

  $(".add-mt-btn").on("click", function () {
    let index = $(".mt_file").length + 1;
    if (index > 3) return; // No more than 2 MT files

    let template = document.importNode(
      document.querySelector("#mt-file-template").content,
      true
    );
    $(template).find(".mt-file-row").attr("id", `mt-file-row-${index}`);
    $(template)
      .find(".mt-file")
      .attr("id", `mt-file-${index}`)
      .attr("name", `mt-file-${index}`);
    $(template).find("label").attr("for", `mt-file-${index}`);

    $(template)
      .find(".remove-mt-btn")
      .on("click", function () {
        $(`#mt-file-row-${index}`).remove();
      });

    $(template)
      .find(".custom-file input[type=file]")
      .each(function (i, el) {
        if (el.files.length > 0) {
          $(el)
            .closest(".custom-file")
            .find(".custom-file-label")
            .html(el.files[0].name);
        }
      });

    $(template)
      .find(".custom-file input[type=file]")
      .on("change", function () {
        $(this)
          .closest(".custom-file")
          .find(".custom-file-label")
          .html(this.files[0].name);
      });

    $(".mt-file-container").append(template);
  });

  $(".add-ht-btn").on("click", function () {
    let index = $(".ht_file").length + 1;
    if (index > 3) return; // No more than 2 MT files

    let template = document.importNode(
      document.querySelector("#ht-file-template").content,
      true
    );
    $(template).find(".ht-file-row").attr("id", `ht-file-row-${index}`);
    $(template)
      .find(".ht-file")
      .attr("id", `ht-file-${index}`)
      .attr("name", `ht-file-${index}`);
    $(template).find("label").attr("for", `ht-file-${index}`);

    $(template)
      .find(".remove-ht-btn")
      .on("click", function () {
        $(`#ht-file-row-${index}`).remove();
      });

    $(template)
      .find(".custom-file input[type=file]")
      .each(function (i, el) {
        if (el.files.length > 0) {
          $(el)
            .closest(".custom-file")
            .find(".custom-file-label")
            .html(el.files[0].name);
        }
      });

    $(template)
      .find(".custom-file input[type=file]")
      .on("change", function () {
        $(this)
          .closest(".custom-file")
          .find(".custom-file-label")
          .html(this.files[0].name);
      });

    $(".ht-file-container").append(template);
  });

  let bpl_chart, bleu_dataset, ter_dataset, chrf_dataset, comet_dataset;

  $(".bleu-btn").on("click", function () {
    $(".scores-btn-group .btn").removeClass("active");
    $(this).addClass("active");

    bpl_chart.config.data.datasets[0] = bleu_dataset;
    bpl_chart.update();
  });

  $(".ter-btn").on("click", function () {
    $(".scores-btn-group .btn").removeClass("active");
    $(this).addClass("active");

    bpl_chart.config.data.datasets[0] = ter_dataset;
    bpl_chart.update();
  });

  $(".chrf-btn").on("click", function () {
    $(".scores-btn-group .btn").removeClass("active");
    $(this).addClass("active");

    bpl_chart.config.data.datasets[0] = chrf_dataset;
    bpl_chart.update();
  });

  $(".comet-btn").on("click", function () {
    $(".scores-btn-group .btn").removeClass("active");
    $(this).addClass("active");

    bpl_chart.config.data.datasets[0] = comet_dataset;
    bpl_chart.update();
  });

  let bpl_table;
  $(".evaluate-form").on("submit", function () {
    $(".evaluate-hint").addClass("d-none");

    // Clean previous
    $(".evaluate-results").addClass("d-none");
    $(".evaluate-results-row").empty();
    $(".chart-select").empty();
    $(".results-select").empty();

    if (bpl_table) bpl_table.clear().draw();

    let data = new FormData();
    data.append("source_file", document.querySelector("#source_file").files[0]);

    mt_filenames = [];
    $(".mt_file").each(function (i, el) {
      if (el.files.length > 0) {
        data.append("mt_files[]", el.files[0]);
        mt_filenames.push(el.files[0].name);
      }
    });

    ht_filenames = [];
    $(".ht_file").each(function (i, el) {
      if (el.files.length > 0) {
        data.append("ht_files[]", el.files[0]);
        ht_filenames.push(el.files[0].name);
      }
    });

    $(".evaluate-status").attr("data-status", "pending");

    let show_results = (evaluation, task_id, mt_ix, ht_ix) => {
      // Clean previous
      $(".evaluate-results").addClass("d-none");
      $(".evaluate-results-row").empty();
      $(".chart-select").empty();

      if (bpl_table) bpl_table.destroy();

      $(".btn-xlsx-download").attr("href", `download/${task_id}/${ht_ix}`);

      for (let _eval of evaluation.evals[mt_ix][ht_ix]) {
        if (_eval.is_metric) {
          let template = document.importNode(
            document.querySelector("#metric-template").content,
            true
          );
          let [min, value, max] = _eval.value;
          let reversed = min > max;

          if (reversed) {
            // Normally, min is the worst value and max is the best
            // In the case those values come reversed (for example [100, 50, 0])
            // it means that min is the best value and max is the worst (e.g. TER scores)
            // So we reverse the progress bar in the UI

            $(template).find(".metric-hint").addClass("reversed");

            let min_aux = min;
            min = max;
            max = min_aux;
          }

          let proportion = max - min;
          let norm_value =
            (100 * (value > max ? max : value < min ? min : value)) /
            proportion;

          $(template).find(".metric-name").html(_eval.name);
          $(template).find(".metric-value").html(value);
          $(template)
            .find(".metric-indicator")
            .css({ left: `calc(${norm_value}% - 8px)` });
          $(".evaluate-results-row").append(template);
        } else {
          let [min, value, max] = _eval.value;
          if (_eval.name == "MT") {
            $(".mt-lexical-value").html(value);
          } else if (_eval.name == "REF") {
            $(".ht-lexical-value").html(value);
          }
        }
      }

      $("#bleu-chart").remove();
      $("#ter-chart").remove();
      $("#comet-chart").remove();
      $("#chrf-chart").remove();

      let bleuChartEl = document.createElement("div");
      bleuChartEl.setAttribute("id", "bleu-chart");

      let terChartEl = document.createElement("div");
      terChartEl.setAttribute("id", "ter-chart");

      let cometChartEl = document.createElement("div");
      cometChartEl.setAttribute("id", "comet-chart");

      let chrfChartEl = document.createElement("div");
      chrfChartEl.setAttribute("id", "chrf-chart");

      $(".chart-container").append(bleuChartEl);
      $(".chart-container").append(terChartEl);
      $(".chart-container").append(cometChartEl);
      $(".chart-container").append(chrfChartEl);

      let file_series = { bleu: [], ter: [], chrf: [], comet: [] };

      file_series["bleu"] = evaluation.spl[ht_ix].map((m) =>
        Number(m[5][mt_ix]["bleu"])
      );
      file_series["ter"] = evaluation.spl[ht_ix].map((m) =>
        parseFloat(m[5][mt_ix]["ter"])
      );

      file_series["comet"] = evaluation.spl[ht_ix].map((m) =>
        parseFloat(parseFloat(m[5][mt_ix]["comet"]).toFixed(2))
      );
      file_series["chrf"] = evaluation.spl[ht_ix].map((m) =>
        parseFloat(m[5][mt_ix]["chrf3"])
      );

      class ChartPaginator {
        constructor(chartId, options = {}, color) {
          // Check if container exists before proceeding
          const container = document.querySelector(`#${chartId}`);
          if (!container) {
            console.error(`Chart container ${chartId} not found`);
            return null;
          }

          // Initialize chart with proper options
          this.chart = new ApexCharts(container, {
            chart: {
              type: 'bar',
              height: 400,
              width: '100%',
              parentHeightOffset: 0,
              toolbar: {
                show: false
              }
            },
            colors: [color],
            series: [{
              name: 'Values',
              data: []
            }],
            xaxis: {
              type: 'category',
              labels: {
                rotate: -45,
                style: {
                  fontSize: '12px'
                }
              }
            },
            yaxis: {
              title: {
                text: 'Value'
              }
            },
            responsive: [{
              breakpoint: 480,
              options: {
                chart: {
                  width: '100%'
                },
                legend: {
                  position: 'bottom'
                }
              }
            }]
          });

          // Render immediately
          this.chart.render();

          // Initialize state
          this.currentPage = 1;
          this.itemsPerPage = parseInt(document.querySelector(`[data-chart="${chartId}"].itemsPerPage`).value);
          this.totalItems = 0;
          this.originalData = [];

          // Store chart ID directly
          this.chartId = chartId;

          this.setupEventListeners();
        }

        setupEventListeners() {
          // Use stored chartId instead of accessing chart.options
          document.querySelector(`[data-chart="${this.chartId}"].prevBtn`).addEventListener('click', () => this.navigatePage(-1));
          document.querySelector(`[data-chart="${this.chartId}"].nextBtn`).addEventListener('click', () => this.navigatePage(1));
          document.querySelector(`[data-chart="${this.chartId}"].itemsPerPage`).addEventListener('change', () => this.handleItemsPerPageChange());
        }

        handleItemsPerPageChange() {
          const newItemsPerPage = parseInt(document.querySelector(`[data-chart="${this.chartId}"].itemsPerPage`).value);
          this.itemsPerPage = newItemsPerPage;
          this.currentPage = 1;
          this.updateDisplay();
          this.refreshChart();
        }

        updateData(data) {
          this.totalItems = data.length;
          this.originalData = data;
          this.updateDisplay();
          this.refreshChart();
        }

        getCurrentPageData() {
          const startIndex = (this.currentPage - 1) * this.itemsPerPage;
          const endIndex = Math.min(startIndex + this.itemsPerPage, this.totalItems);
          return this.originalData.slice(startIndex, endIndex);
        }

        updateDisplay() {
          const totalPages = Math.ceil(this.totalItems / this.itemsPerPage);

          document.querySelector(`[data-chart="${this.chartId}"].pageInfo`).textContent =
            `${(this.currentPage * this.itemsPerPage - this.itemsPerPage + 1)}-${Math.min(this.currentPage * this.itemsPerPage, this.totalItems)} of ${this.totalItems}`;

          document.querySelector(`[data-chart="${this.chartId}"].prevBtn`).disabled = this.currentPage <= 1;
          document.querySelector(`[data-chart="${this.chartId}"].nextBtn`).disabled = this.currentPage >= totalPages;
        }

        navigatePage(direction) {
          if ((direction === -1 && this.currentPage > 1) ||
            (direction === 1 && this.currentPage < Math.ceil(this.totalItems / this.itemsPerPage))) {
            this.currentPage += direction;
            this.updateDisplay();
            this.refreshChart();
          }
        }

        refreshChart() {
          const currentPageData = this.getCurrentPageData();
          if (currentPageData.length === 0) return;

          this.chart.updateOptions({
            series: [{
              data: currentPageData.map(item => ({
                x: item.x,
                y: item.y
              }))
            }],
            xaxis: {
              categories: currentPageData.map(item => item.x),
              labels: {
                rotate: -45,
                rotateAlways: true,
                hideOverlappingLabels: true
              }
            }
          }, false, true);
        }
      }

      // Initialize all charts with proper error handling
      // Sample data for each chart with different values and categories
      const chartData = {
        chart1: file_series["bleu"].splice(0, 100).map((el, i) => ({
          x: `Sent ${i + 1}`,
          y: el
        })),
        chart2: file_series["chrf"].splice(0, 100).map((el, i) => ({
          x: `Sent ${i + 1}`,
          y: el
        })),
        chart3: file_series["ter"].splice(0, 100).map((el, i) => ({
          x: `Sent ${i + 1}`,
          y: el
        })),
        chart4: file_series["comet"].splice(0, 100).map((el, i) => ({
          x: `Sent ${i + 1}`,
          y: el
        }))
      };

      // Initialize all charts with proper error handling
      const charts = [
        new ChartPaginator('chart1', {
          chart: {
            type: 'bar',
            height: 400,
            width: '100%',
            parentHeightOffset: 0,
            toolbar: {
              show: false
            }
          }
        }, "#0F95E1"),
        new ChartPaginator('chart2', {
          chart: {
            type: 'bar',
            height: 400,
            width: '100%',
            parentHeightOffset: 0,
            toolbar: {
              show: false
            }
          }
        }, "#4CE895"),
        new ChartPaginator('chart3', {
          chart: {
            type: 'bar',
            height: 400,
            width: '100%',
            parentHeightOffset: 0,
            toolbar: {
              show: false
            }
          }
        }, "#006293"),
        new ChartPaginator('chart4', {
          chart: {
            type: 'bar',
            height: 400,
            width: '100%',
            parentHeightOffset: 0,
            toolbar: {
              show: false
            }
          }
        }, "#259887")
      ];

      // Filter out null values and initialize only valid charts
      const validCharts = charts.filter(chart => chart !== null);

      // Add small delay to ensure DOM is ready
      setTimeout(() => {
        validCharts.forEach((chart, index) => {
          const chartId = chart.chartId;
          // Update chart with its specific data
          chart.updateData(chartData[chartId]);
        });
      }, 100);





      $(".evaluate-status").attr("data-status", "none");
      $(".evaluate-results").removeClass("d-none");


      $(".page-number").attr("max", evaluation.spl[ht_ix].length);
      bpl_table = $(".bleu-line").DataTable({
        data: evaluation.spl[ht_ix],
        dom: "tp",
        pageLength: 1,
        responsive: true,
        autoWidth: false,
        scrollX: true,
        pagingType: "full",
        drawCallback: function (settings) {
          let api = this.api();
          let rows = api.rows({ page: "current" }).nodes();
          let row_data = api.rows({ page: "current" }).data();

          $(".page-number").val(api.page() + 1);

          rows.each(function (row, i) {
            let data = row_data[i];

            let sentences_data = data[5];

            if (data.length > 6) {
              let template = document.importNode(
                document.querySelector("#sentences-view-template").content,
                true
              );
              $(template).find(".sentences-view-source").html(data[6]);
              $(row).before(template);
            }

            let ix = 1;
            for (sentence_data of sentences_data) {
              let mt_template = document.importNode(
                document.querySelector("#sentences-view-mt-template").content,
                true
              );
              $(mt_template).find(".sentences-view-mt-index").html(ix);
              $(mt_template)
                .find(".sentences-view-mt")
                .html(sentence_data.text);
              $(mt_template)
                .find(".sentences-view-bleu")
                .html(sentence_data.bleu);
              $(mt_template)
                .find(".sentences-view-ter")
                .html(sentence_data.ter);
              $(mt_template)
                .find(".sentences-view-comet")
                .html(sentence_data.comet);
              $(mt_template)
                .find(".sentences-view-chrf")
                .html(sentence_data.chrf3);
              $(row).before(mt_template);

              ix++;
            }

            // // if (data.length > 6) {
            // let templateRef = document.importNode(
            //   document.querySelector("#sentences-view-ref-template").content,
            //   true
            // );
            // $(templateRef).find(".sentences-view-ref").html(data[1]);
            // $(row).before(templateRef);
            // // }
            $(".score-table-line-no").html(data[4]);

            $(".odd td:last").prev().html("");

            $(".odd td:last").html("");

            this.columns.adjust();
          });
        },
        columnDefs: [
          {
            targets: "_all",
            orderable: false,
          },
          {
            targets: [0, 1],
            className: "overflow",
          },
          {
            targets: 0,
            render: function (data, type, row) {
              return data ? "<strong>" + data + "</strong>" : "";
            },
          },
        ],
      });

      $(".page-btn").on("click", function () {
        let page_val = parseInt($(".page-number").val()) - 1;
        bpl_table.page(page_val).draw(false);
      });
    };

    //! END OF TABLE

    $.ajax({
      url: $(this).attr("action"),
      method: "POST",
      data: data,
      contentType: false,
      cache: false,
      processData: false,
      beforeSend: function () {
        $(".evaluate-form").find("input").prop('disabled', true);

        $(".evaluate-form").find("input").addClass("disabled-link");
        $(".evaluate-form").find("a").off('click');
        $(".evaluate-form").find("a").addClass("disabled-link");

      },
      success: function (data) {
        if (data.result == 200) {
          longpoll(
            2000,
            {
              url: "get_evaluation",
              method: "POST",
              data: { task_id: data.task_id },
            },
            (data) => {
              if (data.result == 200) {
                let evaluation = data.evaluation;

                for (let i = 0; i < mt_filenames.length; i++) {
                  let opt_el = document.createElement("option");
                  $(opt_el).attr("value", i).html(mt_filenames[i]);
                  $(".results-mt-select").append(opt_el);
                }

                for (let i = 0; i < ht_filenames.length; i++) {
                  let opt_el = document.createElement("option");
                  $(opt_el).attr("value", i).html(ht_filenames[i]);
                  $(".results-ht-select").append(opt_el);
                }

                $(".btn-xlsx-download").attr(
                  "href",
                  `download/${data.task_id}/0`
                );

                show_results(evaluation, data.task_id, 0, 0);

                $(".results-select")
                  .off("change")
                  .on("change", function () {
                    show_results(
                      evaluation,
                      data.task_id,
                      $(".results-mt-select option:selected").val(),
                      $(".results-ht-select option:selected").val()
                    );
                  });

                return false;
              }
            }
          );
        } else {
          $(".evaluate-status").attr("data-status", "error");
          $(".evaluate-form").find("input").prop('disabled', false);
          $(".evaluate-form").find("input").removeClass("disabled-link");
          $(".evaluate-form").find("a").on('click');
          $(".evaluate-form").find("a").removeClass("disabled-link");
        }
      },
    });

    return false;
  });
});

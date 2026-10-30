/**
 * GRIDWISE AI - Comprehensive Technical Microgrid Chart Library
 * Built with Plotly.js for the Professional Enterprise White Theme.
 * Visualizes 8760-hour synthetic datasets & 500 stochastic scenarios (800 kWp PV, 1000 kWh BESS, 1000 kW Grid).
 */

const GridWiseCharts = {
    // Theme palette configuration (Strict Professional White Theme)
    colors: {
        primaryGreen: '#16A34A',
        primaryGreenHover: '#15803D',
        secondaryTeal: '#0D9488',
        blue: '#0284C7',
        amber: '#D97706',
        purple: '#7C3AED',
        red: '#DC2626',
        gray: '#94A3B8',
        lightGray: '#F1F5F9',
        gridLine: '#E2E8F0',
        text: '#475569',
        heading: '#172B4D'
    },

    // Standard 24-hour time axis
    hours24: Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`),

    // Base layout settings
    getBaseLayout(overrides = {}) {
        return {
            font: {
                family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                size: 11,
                color: this.colors.text
            },
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            margin: { t: 30, r: 25, l: 55, b: 42 },
            hovermode: 'x unified',
            hoverlabel: {
                bgcolor: '#FFFFFF',
                bordercolor: '#CBD5E1',
                font: { family: 'inherit', size: 12, color: '#172B4D' }
            },
            showlegend: true,
            legend: {
                orientation: 'h',
                y: -0.22,
                x: 0.05,
                font: { size: 10, color: this.colors.text }
            },
            xaxis: {
                gridcolor: this.colors.lightGray,
                linecolor: this.colors.gridLine,
                tickfont: { size: 10, color: this.colors.gray },
                zeroline: false
            },
            yaxis: {
                gridcolor: this.colors.lightGray,
                linecolor: this.colors.gridLine,
                tickfont: { size: 10, color: this.colors.gray },
                zeroline: false
            },
            ...overrides
        };
    },

    // Base Plotly config options
    baseConfig: {
        responsive: true,
        displayModeBar: false
    },

    // Cached dataset fetched from backend API
    datasetCache: null,
    riskCache: null,
    batteryCache: null,
    costCache: null,
    energyCache: null,

    async fetchDataset() {
        if (this.datasetCache) return this.datasetCache;
        try {
            const resp = await fetch('/api/dataset/charts');
            if (resp.ok) {
                this.datasetCache = await resp.json();
                return this.datasetCache;
            }
        } catch (e) {
            console.warn('Could not fetch dataset API, using client fallback baseline:', e);
        }
        return null;
    },

    async fetchRiskData() {
        if (this.riskCache) return this.riskCache;
        try {
            const resp = await fetch('/api/analytics/risk');
            if (resp.ok) {
                this.riskCache = await resp.json();
                return this.riskCache;
            }
        } catch (e) {
            console.warn('Could not fetch risk API:', e);
        }
        return null;
    },

    async fetchBatteryData() {
        if (this.batteryCache) return this.batteryCache;
        try {
            const resp = await fetch('/api/analytics/battery');
            if (resp.ok) {
                this.batteryCache = await resp.json();
                return this.batteryCache;
            }
        } catch (e) {
            console.warn('Could not fetch battery API:', e);
        }
        return null;
    },

    async fetchCostData() {
        if (this.costCache) return this.costCache;
        try {
            const resp = await fetch('/api/analytics/cost');
            if (resp.ok) {
                this.costCache = await resp.json();
                return this.costCache;
            }
        } catch (e) {
            console.warn('Could not fetch cost API:', e);
        }
        return null;
    },

    async fetchEnergyData() {
        if (this.energyCache) return this.energyCache;
        try {
            const resp = await fetch('/api/analytics/energy');
            if (resp.ok) {
                this.energyCache = await resp.json();
                return this.energyCache;
            }
        } catch (e) {
            console.warn('Could not fetch energy API:', e);
        }
        return null;
    },

    /* ==========================================================================
       THE 8 SPECIFIC PHASE 3 REQUIRED PLOTLY CHARTS
       ========================================================================== */

    // 1. 24-Hour Campus Demand Curve (kW)
    async render24HourDemandCurve(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const data = await this.fetchDataset();
        const demandActual = data?.demand_24h_actual || [230, 215, 210, 205, 215, 260, 360, 520, 720, 840, 890, 915, 870, 860, 910, 925, 880, 740, 620, 540, 460, 390, 310, 260];
        const demandBase = data?.demand_24h_base || demandActual.map(v => Math.round(v * 0.96));

        const traces = [
            {
                x: this.hours24,
                y: demandActual,
                name: 'Actual Campus Demand (kW)',
                type: 'scatter',
                mode: 'lines+markers',
                marker: { size: 5, color: this.colors.primaryGreen },
                line: { width: 2.5, color: this.colors.primaryGreen }
            },
            {
                x: this.hours24,
                y: demandBase,
                name: 'Base Diurnal Load (kW)',
                type: 'scatter',
                mode: 'lines',
                line: { width: 1.5, color: this.colors.gray, dash: 'dot' }
            }
        ];

        const layout = this.getBaseLayout({
            title: { text: '24-Hour Campus Electricity Demand Profile', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Demand (kW)', gridcolor: this.colors.lightGray }
        });

        Plotly.newPlot(el, traces, layout, this.baseConfig);
    },

    // 2. 24-Hour Solar Generation Curve (kW)
    async render24HourSolarCurve(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const data = await this.fetchDataset();
        const solarActual = data?.solar_24h || [0,0,0,0,0,0, 42, 135, 310, 510, 645, 715, 690, 580, 430, 230, 90, 15, 0,0,0,0,0,0];
        const clearSkyModel = solarActual.map(v => Math.round(v * 1.08));

        const traces = [
            {
                x: this.hours24,
                y: solarActual,
                name: 'Photovoltaic Output (kW)',
                type: 'scatter',
                mode: 'lines',
                fill: 'tozeroy',
                fillcolor: 'rgba(217, 119, 6, 0.20)',
                line: { width: 2.5, color: this.colors.amber }
            },
            {
                x: this.hours24,
                y: clearSkyModel,
                name: 'Clear-Sky Upper Bound (800 kWp)',
                type: 'scatter',
                mode: 'lines',
                line: { width: 1.5, color: this.colors.gray, dash: 'dash' }
            }
        ];

        const layout = this.getBaseLayout({
            title: { text: '24-Hour Solar PV Production Curve (800 kWp Array)', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Solar Generation (kW)', range: [0, 850], gridcolor: this.colors.lightGray }
        });

        Plotly.newPlot(el, traces, layout, this.baseConfig);
    },

    // 3. Daily Energy Consumption Chart (kWh)
    async renderDailyEnergyConsumption(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const data = await this.fetchDataset();
        const dates = data?.daily_dates || Array.from({ length: 30 }, (_, i) => `Oct ${i+1}`);
        const totals = data?.daily_demand_totals || Array.from({ length: 30 }, () => 11500 + Math.random() * 800 - 400);

        const trace = {
            x: dates,
            y: totals,
            name: 'Daily Campus Electricity (kWh)',
            type: 'bar',
            marker: { color: this.colors.secondaryTeal }
        };

        const layout = this.getBaseLayout({
            title: { text: 'Daily Campus Electricity Consumption (30-Day View)', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Total Consumption (kWh / Day)', gridcolor: this.colors.lightGray }
        });

        Plotly.newPlot(el, [trace], layout, this.baseConfig);
    },

    // 4. Solar Generation by Weather Condition (kW)
    async renderSolarByWeatherCondition(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const data = await this.fetchDataset();
        const weather = data?.solar_by_weather || {
            Sunny: [0,0,0,0,0,0, 45, 150, 350, 560, 710, 760, 740, 640, 480, 260, 100, 20, 0,0,0,0,0,0],
            "Partly Cloudy": [0,0,0,0,0,0, 30, 110, 260, 430, 560, 610, 580, 500, 370, 200, 75, 12, 0,0,0,0,0,0],
            Cloudy: [0,0,0,0,0,0, 15, 55, 140, 230, 310, 340, 320, 280, 200, 110, 40, 6, 0,0,0,0,0,0],
            Rainy: [0,0,0,0,0,0, 5, 20, 50, 80, 110, 120, 115, 95, 70, 35, 15, 2, 0,0,0,0,0,0]
        };

        const traces = [
            {
                x: this.hours24,
                y: weather.Sunny,
                name: 'Sunny (Clear Sky)',
                type: 'scatter',
                mode: 'lines',
                line: { width: 2.5, color: this.colors.amber }
            },
            {
                x: this.hours24,
                y: weather["Partly Cloudy"],
                name: 'Partly Cloudy',
                type: 'scatter',
                mode: 'lines',
                line: { width: 2, color: this.colors.secondaryTeal }
            },
            {
                x: this.hours24,
                y: weather.Cloudy,
                name: 'Cloudy',
                type: 'scatter',
                mode: 'lines',
                line: { width: 2, color: this.colors.blue }
            },
            {
                x: this.hours24,
                y: weather.Rainy,
                name: 'Rainy (Heavy Overcast)',
                type: 'scatter',
                mode: 'lines',
                line: { width: 2, color: this.colors.red, dash: 'dash' }
            }
        ];

        const layout = this.getBaseLayout({
            title: { text: 'Solar PV Generation Under Discrete Weather Conditions (kW)', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Generation (kW)', range: [0, 850], gridcolor: this.colors.lightGray }
        });

        Plotly.newPlot(el, traces, layout, this.baseConfig);
    },

    // 5. Electricity Price by Hour (INR/kWh)
    async renderElectricityPriceByHour(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const data = await this.fetchDataset();
        const daPrices = data?.prices_da_inr || [4.20, 4.20, 4.20, 4.20, 4.20, 4.20, 7.50, 7.50, 7.50, 7.50, 7.50, 7.50, 7.50, 7.50, 11.80, 11.80, 11.80, 11.80, 11.80, 11.80, 7.50, 7.50, 4.20, 4.20];
        const rtPrices = data?.prices_rt_inr || daPrices.map((v, i) => i >= 14 && i <= 19 ? v + 0.85 : v + 0.25);

        const traces = [
            {
                x: this.hours24,
                y: daPrices,
                name: 'Day-Ahead Tariff (INR/kWh)',
                type: 'bar',
                marker: { color: 'rgba(2, 132, 199, 0.65)' }
            },
            {
                x: this.hours24,
                y: rtPrices,
                name: 'Real-Time Spot Price (INR/kWh)',
                type: 'scatter',
                mode: 'lines+markers',
                marker: { size: 5, color: this.colors.red },
                line: { width: 2, color: this.colors.red }
            }
        ];

        const layout = this.getBaseLayout({
            title: { text: 'Simulated Time-of-Use Electricity Tariff Schedule', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Tariff (INR / kWh)', gridcolor: this.colors.lightGray }
        });

        Plotly.newPlot(el, traces, layout, this.baseConfig);
    },

    // 6. Demand Scenario Distribution (500 Scenarios)
    async renderDemandScenarioDistribution(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const data = await this.fetchDataset();
        const p10 = data?.demand_p10 || [205, 190, 185, 180, 190, 230, 315, 460, 635, 740, 785, 805, 765, 755, 800, 815, 775, 650, 545, 475, 405, 345, 275, 230];
        const p50 = data?.demand_p50 || [230, 215, 210, 205, 215, 260, 360, 520, 720, 840, 890, 915, 870, 860, 910, 925, 880, 740, 620, 540, 460, 390, 310, 260];
        const p90 = data?.demand_p90 || [255, 240, 235, 230, 240, 290, 405, 580, 805, 940, 995, 1025, 975, 965, 1020, 1035, 985, 830, 695, 605, 515, 435, 345, 290];

        const traces = [
            {
                x: this.hours24,
                y: p90,
                name: 'P90 Upper Demand Band',
                type: 'scatter',
                mode: 'lines',
                line: { width: 0 },
                showlegend: false
            },
            {
                x: this.hours24,
                y: p10,
                name: 'P10 - P90 Uncertainty Envelope',
                type: 'scatter',
                mode: 'lines',
                fill: 'tonexty',
                fillcolor: 'rgba(22, 163, 74, 0.15)',
                line: { width: 0 }
            },
            {
                x: this.hours24,
                y: p50,
                name: 'P50 Median Campus Demand (kW)',
                type: 'scatter',
                mode: 'lines+markers',
                marker: { size: 4 },
                line: { width: 2.5, color: this.colors.primaryGreen }
            }
        ];

        const layout = this.getBaseLayout({
            title: { text: 'Campus Demand Stochastic Uncertainty Fan (500 Scenarios)', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Demand (kW)', gridcolor: this.colors.lightGray }
        });

        Plotly.newPlot(el, traces, layout, this.baseConfig);
    },

    // 7. Solar Uncertainty Distribution (P10, P50, P90)
    async renderSolarUncertaintyDistribution(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const data = await this.fetchDataset();
        const p10 = data?.solar_p10 || [0,0,0,0,0,0, 25, 80, 190, 310, 405, 450, 430, 360, 270, 140, 55, 8, 0,0,0,0,0,0];
        const p50 = data?.solar_p50 || [0,0,0,0,0,0, 42, 135, 310, 510, 645, 715, 690, 580, 430, 230, 90, 15, 0,0,0,0,0,0];
        const p90 = data?.solar_p90 || [0,0,0,0,0,0, 52, 165, 380, 620, 755, 795, 780, 670, 510, 280, 110, 20, 0,0,0,0,0,0];

        const traces = [
            {
                x: this.hours24,
                y: p90,
                name: 'P90 Optimistic Yield',
                type: 'scatter',
                mode: 'lines',
                line: { width: 0 },
                showlegend: false
            },
            {
                x: this.hours24,
                y: p10,
                name: 'P10 - P90 Irradiance Band',
                type: 'scatter',
                mode: 'lines',
                fill: 'tonexty',
                fillcolor: 'rgba(217, 119, 6, 0.18)',
                line: { width: 0 }
            },
            {
                x: this.hours24,
                y: p50,
                name: 'P50 Expected Solar Output (kW)',
                type: 'scatter',
                mode: 'lines+markers',
                marker: { size: 4 },
                line: { width: 2.5, color: this.colors.amber }
            }
        ];

        const layout = this.getBaseLayout({
            title: { text: 'Solar Generation Uncertainty Envelope (500 Scenarios)', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Solar PV Output (kW)', range: [0, 850], gridcolor: this.colors.lightGray }
        });

        Plotly.newPlot(el, traces, layout, this.baseConfig);
    },

    // 8. Scenario Probability Distribution
    async renderScenarioProbabilityDistribution(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const data = await this.fetchDataset();
        const labels = data?.weather_labels || ['Sunny', 'Partly Cloudy', 'Cloudy', 'Rainy'];
        const probs = data?.weather_probs || [0.35, 0.30, 0.20, 0.15];
        const counts = [175, 150, 100, 75];

        const trace = {
            x: labels,
            y: probs,
            type: 'bar',
            marker: {
                color: [this.colors.amber, this.colors.secondaryTeal, this.colors.blue, this.colors.red]
            },
            text: probs.map((p, i) => `${(p * 100).toFixed(0)}% (${counts[i]} sc.)`),
            textposition: 'auto'
        };

        const layout = this.getBaseLayout({
            title: { text: 'Weather Condition Scenario Probabilities (N = 500)', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Probability Weight (π_ω)', range: [0, 0.45], tickformat: ',.0%' }
        });

        Plotly.newPlot(el, [trace], layout, this.baseConfig);
    },

    /* ==========================================================================
       PAGE SPECIFIC CHARTS (INTEGRATED WITH PHASE 3 SYNTHETIC DATASETS)
       ========================================================================== */

    // Overview 24h Energy Balance
    async renderOverviewBalance(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const data = await this.fetchDataset();
        const demand = data?.demand_24h_actual || [230, 215, 210, 205, 215, 260, 360, 520, 720, 840, 890, 915, 870, 860, 910, 925, 880, 740, 620, 540, 460, 390, 310, 260];
        const solar = data?.solar_24h || [0,0,0,0,0,0, 42, 135, 310, 510, 645, 715, 690, 580, 430, 230, 90, 15, 0,0,0,0,0,0];
        
        // Storage discharge strategy (discharges during on-peak 14:00 - 19:00)
        const batteryDischarge = [0,0,0,0,0,0, 0, 0, 0, 0, 0, 0, 0, 0, 190, 250, 280, 250, 190, 110, 30, 0, 0, 0];
        
        // Grid import balances the remainder
        const gridImport = demand.map((d, i) => Math.max(0, d - solar[i] - batteryDischarge[i]));

        const traces = [
            {
                x: this.hours24,
                y: solar,
                name: 'Solar PV Direct (kW)',
                type: 'scatter',
                mode: 'lines',
                stackgroup: 'supply',
                fillcolor: 'rgba(217, 119, 6, 0.45)',
                line: { width: 1.5, color: this.colors.amber }
            },
            {
                x: this.hours24,
                y: batteryDischarge,
                name: 'BESS Discharge (kW)',
                type: 'scatter',
                mode: 'lines',
                stackgroup: 'supply',
                fillcolor: 'rgba(124, 58, 237, 0.45)',
                line: { width: 1.5, color: this.colors.purple }
            },
            {
                x: this.hours24,
                y: gridImport,
                name: 'Grid Import (kW)',
                type: 'scatter',
                mode: 'lines',
                stackgroup: 'supply',
                fillcolor: 'rgba(2, 132, 199, 0.35)',
                line: { width: 1.5, color: this.colors.blue }
            },
            {
                x: this.hours24,
                y: demand,
                name: 'Campus Demand (kW)',
                type: 'scatter',
                mode: 'lines',
                line: { width: 2.5, color: this.colors.red, dash: 'solid' }
            }
        ];

        const layout = this.getBaseLayout({
            title: { text: '24-Hour Microgrid Power Balance', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Power Flow (kW)', gridcolor: this.colors.lightGray }
        });

        Plotly.newPlot(el, traces, layout, this.baseConfig);
    },

    // Overview Solar vs Demand
    async renderOverviewSolarVsDemand(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const data = await this.fetchDataset();
        const solar = data?.solar_24h || [0,0,0,0,0,0, 42, 135, 310, 510, 645, 715, 690, 580, 430, 230, 90, 15, 0,0,0,0,0,0];
        const demand = data?.demand_24h_actual || [230, 215, 210, 205, 215, 260, 360, 520, 720, 840, 890, 915, 870, 860, 910, 925, 880, 740, 620, 540, 460, 390, 310, 260];

        const traces = [
            {
                x: this.hours24,
                y: solar,
                name: 'Solar Generation (kW)',
                type: 'scatter',
                mode: 'lines+markers',
                marker: { size: 4 },
                line: { width: 2.5, color: this.colors.amber }
            },
            {
                x: this.hours24,
                y: demand,
                name: 'Campus Demand (kW)',
                type: 'scatter',
                mode: 'lines+markers',
                marker: { size: 4 },
                line: { width: 2.5, color: this.colors.secondaryTeal }
            }
        ];

        const layout = this.getBaseLayout({
            title: { text: 'Solar PV Production vs. Campus Load', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Power (kW)', gridcolor: this.colors.lightGray }
        });

        Plotly.newPlot(el, traces, layout, this.baseConfig);
    },

    // Overview Energy Source Distribution
    renderOverviewSourceDistribution(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const trace = {
            values: [8314, 3285, 1120],
            labels: ['Grid Import', 'Solar Direct', 'BESS Storage'],
            type: 'pie',
            hole: 0.55,
            marker: {
                colors: [this.colors.blue, this.colors.amber, this.colors.primaryGreen]
            },
            textinfo: 'label+percent',
            textposition: 'outside',
            insidetextorientation: 'radial'
        };

        const layout = {
            ...this.getBaseLayout(),
            showlegend: false,
            margin: { t: 20, r: 20, l: 20, b: 20 }
        };

        Plotly.newPlot(el, [trace], layout, this.baseConfig);
    },

    // Overview Daily Cost Summary
    renderOverviewDailyCost(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const hourlyCostINR = [966, 903, 882, 861, 903, 1092, 2700, 3900, 5400, 6300, 6675, 6862, 6525, 6450, 10738, 10915, 10384, 8732, 7316, 6372, 3450, 2925, 1302, 1092];
        const barColors = hourlyCostINR.map((_, i) => {
            if (i >= 14 && i <= 19) return this.colors.red;
            if ((i >= 6 && i < 14) || (i >= 20 && i < 22)) return this.colors.secondaryTeal;
            return this.colors.blue;
        });

        const trace = {
            x: this.hours24,
            y: hourlyCostINR,
            name: 'Hourly Spend (INR)',
            type: 'bar',
            marker: { color: barColors }
        };

        const layout = this.getBaseLayout({
            title: { text: 'Daily Energy Spend Across Time-of-Use Periods', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Hourly Spend (INR)', gridcolor: this.colors.lightGray }
        });

        Plotly.newPlot(el, [trace], layout, this.baseConfig);
    },

    // Monitoring Page Charts
    renderMonitoringDemand(containerId) {
        this.render24HourDemandCurve(containerId);
    },
    renderMonitoringSolar(containerId) {
        this.render24HourSolarCurve(containerId);
    },
    renderMonitoringBattery(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const batteryPower = [180, 200, 220, 200, 160, 0, 0, 0, 0, 0, -40, -70, 0, 0, -190, -250, -280, -250, -190, -110, -30, 0, 120, 150];
        const trace = {
            x: this.hours24,
            y: batteryPower,
            name: 'Net Battery Power (kW)',
            type: 'bar',
            marker: {
                color: batteryPower.map(v => v >= 0 ? this.colors.primaryGreen : this.colors.purple)
            }
        };

        const layout = this.getBaseLayout({
            title: { text: 'BESS Charge (+) & Discharge (-) Power (kW)', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Battery Power (kW)', gridcolor: this.colors.lightGray }
        });

        Plotly.newPlot(el, [trace], layout, this.baseConfig);
    },
    renderMonitoringGrid(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const gridImport = [230, 215, 210, 205, 215, 260, 318, 385, 410, 330, 245, 200, 180, 280, 290, 390, 470, 490, 430, 430, 430, 390, 310, 260];
        const limit = Array(24).fill(1000);

        const traces = [
            {
                x: this.hours24,
                y: gridImport,
                name: 'Grid Import (kW)',
                type: 'scatter',
                mode: 'lines',
                fill: 'tozeroy',
                fillcolor: 'rgba(2, 132, 199, 0.12)',
                line: { width: 2, color: this.colors.blue }
            },
            {
                x: this.hours24,
                y: limit,
                name: 'Feeder Contract Limit (1000 kW)',
                type: 'scatter',
                mode: 'lines',
                line: { width: 2, color: this.colors.red, dash: 'dash' }
            }
        ];

        const layout = this.getBaseLayout({
            title: { text: 'Utility Grid Import vs. 1000 kW Feeder Limit', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Grid Import (kW)', range: [0, 1100], gridcolor: this.colors.lightGray }
        });

        Plotly.newPlot(el, traces, layout, this.baseConfig);
    },

    // Optimization Studio Dispatch Preview (Real Phase 4 Solver Results)
    async renderOptimizationSchedulePreview(containerId, customHourlyData = null) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        let procurement = [0, 0, 0, 0, 0, 0, 0, 0, 180, 240, 280, 310, 290, 260, 320, 350, 380, 340, 260, 190, 110, 45, 0, 0];
        let soc = [50, 56, 62, 68, 72, 70, 68, 62, 55, 48, 42, 38, 35, 30, 25, 20, 18, 16, 16, 20, 28, 38, 44, 50];

        try {
            if (customHourlyData && Array.isArray(customHourlyData) && customHourlyData.length === 24) {
                procurement = customHourlyData.map(r => r.day_ahead_procurement_kw || r.grid_import_kw || 0);
                soc = customHourlyData.map(r => r.expected_battery_soc_pct || r.bess_soc_pct || 50);
            } else {
                const resp = await fetch('/api/optimization/latest');
                if (resp.ok) {
                    const optData = await resp.json();
                    if (optData.hourly_schedule && optData.hourly_schedule.length === 24) {
                        procurement = optData.hourly_schedule.map(r => r.day_ahead_procurement_kw || 0);
                        soc = optData.hourly_schedule.map(r => r.expected_battery_soc_pct || 50);
                    }
                }
            }
        } catch (e) {
            console.warn('Could not load dynamic optimization schedule, using baseline series:', e);
        }

        const traces = [
            {
                x: this.hours24,
                y: procurement,
                name: 'Planned Grid Procurement (kW)',
                type: 'scatter',
                mode: 'lines+markers',
                marker: { size: 5, color: this.colors.primaryGreen },
                line: { width: 2.5, color: this.colors.primaryGreen },
                yaxis: 'y1'
            },
            {
                x: this.hours24,
                y: soc,
                name: 'Planned BESS SoC (%)',
                type: 'scatter',
                mode: 'lines+markers',
                marker: { size: 4, color: this.colors.purple },
                line: { width: 2, color: this.colors.purple, dash: 'dot' },
                yaxis: 'y2'
            }
        ];

        const layout = this.getBaseLayout({
            title: { text: 'Optimal Day-Ahead Dispatch Plan & BESS SoC Trajectory', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Day-Ahead Power (kW)', gridcolor: this.colors.lightGray },
            yaxis2: {
                title: 'State of Charge (%)',
                overlaying: 'y',
                side: 'right',
                range: [0, 100],
                showgrid: false,
                tickfont: { size: 10, color: this.colors.purple }
            }
        });

        Plotly.newPlot(el, traces, layout, this.baseConfig);
    },

    // Scenario Analysis Page Charts
    renderScenarioProbabilities(containerId) {
        this.renderScenarioProbabilityDistribution(containerId);
    },
    renderScenarioSolarComparison(containerId) {
        this.renderSolarByWeatherCondition(containerId);
    },
    renderScenarioDemandComparison(containerId) {
        this.renderDemandScenarioDistribution(containerId);
    },
    renderScenarioCostComparison(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const trace = {
            x: ['Sunny Day', 'Partly Cloudy', 'Cloudy Day', 'Rainy Day'],
            y: [76500, 84200, 96800, 108400],
            name: 'Expected Daily Cost (INR)',
            type: 'bar',
            marker: {
                color: [this.colors.amber, this.colors.secondaryTeal, this.colors.blue, this.colors.red]
            }
        };

        const layout = this.getBaseLayout({
            title: { text: 'Expected Procurement Expenditure by Weather Scenario (INR)', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Procurement Cost (INR / Day)' }
        });

        Plotly.newPlot(el, [trace], layout, this.baseConfig);
    },

    // Risk Management Page Charts
    async renderRiskCostDistribution(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const riskData = await this.fetchRiskData();
        const costs = (riskData?.raw_costs_sample && riskData.raw_costs_sample.length > 0)
            ? riskData.raw_costs_sample
            : [72000, 74500, 75500, 76800, 78200, 79500, 81000, 82500, 83200, 84500,
               85200, 86100, 86800, 87500, 88200, 89100, 90200, 91500, 92800, 93600,
               94800, 96200, 97500, 98800, 100200, 102500, 104200, 106800, 109500, 114000];

        const var95 = riskData?.metrics?.var_95_inr || 101273.67;
        const cvar95 = riskData?.metrics?.cvar_95_inr || 104400.74;

        const histTrace = {
            x: costs,
            type: 'histogram',
            nbinsx: 20,
            name: 'Scenario Cost Density (500 Scenarios)',
            marker: { color: 'rgba(2, 132, 199, 0.65)', line: { color: this.colors.blue, width: 1 } }
        };

        const layout = this.getBaseLayout({
            title: { text: 'Scenario Procurement Cost Density & Tail Risk Bounds (INR)', font: { size: 13, color: this.colors.heading } },
            xaxis: { title: 'Procurement Cost (INR / Day)' },
            yaxis: { title: 'Scenario Frequency' },
            shapes: [
                { type: 'line', x0: var95, x1: var95, y0: 0, y1: 1, yref: 'paper', line: { color: this.colors.amber, width: 2, dash: 'dash' } },
                { type: 'line', x0: cvar95, x1: cvar95, y0: 0, y1: 1, yref: 'paper', line: { color: this.colors.red, width: 2.5, dash: 'solid' } }
            ],
            annotations: [
                { x: var95, y: 0.92, yref: 'paper', text: `VaR (95%): ₹${Math.round(var95).toLocaleString('en-IN')}`, showarrow: true, arrowcolor: this.colors.amber, font: { size: 10, color: this.colors.amber } },
                { x: cvar95, y: 0.78, yref: 'paper', text: `CVaR (95%): ₹${Math.round(cvar95).toLocaleString('en-IN')}`, showarrow: true, arrowcolor: this.colors.red, font: { size: 10, color: this.colors.red } }
            ]
        });

        Plotly.newPlot(el, [histTrace], layout, this.baseConfig);
    },

    async renderRiskVarCvarComparison(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const riskData = await this.fetchRiskData();
        const m = riskData?.metrics || {};

        const varVals = [m.var_90_inr || 95800, m.var_95_inr || 101273.67, m.var_99_inr || 106500];
        const cvarVals = [m.cvar_90_inr || 101400, m.cvar_95_inr || 104400.74, m.cvar_99_inr || 108900];

        const traces = [
            {
                x: ['α = 90%', 'α = 95%', 'α = 99%'],
                y: varVals,
                name: 'Value-at-Risk (VaR)',
                type: 'bar',
                marker: { color: this.colors.amber }
            },
            {
                x: ['α = 90%', 'α = 95%', 'α = 99%'],
                y: cvarVals,
                name: 'Conditional Value-at-Risk (CVaR)',
                type: 'bar',
                marker: { color: this.colors.red }
            }
        ];

        const layout = this.getBaseLayout({
            title: { text: 'VaR vs. CVaR Tail Risk Across Confidence Levels (INR)', font: { size: 13, color: this.colors.heading } },
            barmode: 'group',
            yaxis: { title: 'Tail Loss Bound (INR)' }
        });

        Plotly.newPlot(el, traces, layout, this.baseConfig);
    },

    async renderRiskFrontier(containerId, selectedLambda = 0.0) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const riskData = await this.fetchRiskData();
        const frontier = riskData?.pareto_frontier || [
            { lambda: 0.0, expected_cost_inr: 52227.39, cvar_95_inr: 62173.94 },
            { lambda: 0.25, expected_cost_inr: 52234.90, cvar_95_inr: 62123.85 },
            { lambda: 0.50, expected_cost_inr: 52266.94, cvar_95_inr: 62078.13 },
            { lambda: 0.75, expected_cost_inr: 52360.56, cvar_95_inr: 62038.23 },
            { lambda: 1.00, expected_cost_inr: 60265.68, cvar_95_inr: 62000.03 }
        ];

        const cvarValues = frontier.map(pt => pt.cvar_95_inr);
        const expectedCosts = frontier.map(pt => pt.expected_cost_inr);
        const textLabels = frontier.map(pt => `λ=${pt.lambda}: E[C]=₹${pt.expected_cost_inr.toLocaleString()}, CVaR=₹${pt.cvar_95_inr.toLocaleString()}`);

        const frontierTrace = {
            x: cvarValues,
            y: expectedCosts,
            mode: 'lines+markers',
            text: textLabels,
            hoverinfo: 'text',
            marker: { size: 9, color: this.colors.primaryGreen },
            line: { width: 2.5, color: this.colors.primaryGreen },
            name: 'Pareto Efficient Frontier'
        };

        // Find currently selected point
        const selPt = frontier.find(pt => Math.abs(pt.lambda - selectedLambda) < 0.01) || frontier[0];
        const highlightTrace = {
            x: [selPt.cvar_95_inr],
            y: [selPt.expected_cost_inr],
            mode: 'markers',
            marker: { size: 14, color: this.colors.red, symbol: 'diamond', line: { color: '#FFFFFF', width: 2 } },
            name: `Active Selection (λ = ${selPt.lambda})`
        };

        const layout = this.getBaseLayout({
            title: { text: 'Mean-CVaR Pareto Efficient Frontier (Rockafellar-Uryasev)', font: { size: 13, color: this.colors.heading } },
            xaxis: { title: 'Tail Risk CVaR (95%) in INR (Lower is Safer)', autorange: 'reversed' },
            yaxis: { title: 'Expected Total Cost E[Cost] in INR' }
        });

        Plotly.newPlot(el, [frontierTrace, highlightTrace], layout, this.baseConfig);
    },

    // Battery Page Charts (1000 kWh Capacity)
    async renderBatterySocProfile(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const battData = await this.fetchBatteryData();
        const hourlySoc = battData?.hourly_soc || [];
        const hours = hourlySoc.length > 0 ? hourlySoc.map(h => h.hour_label) : this.hours24;
        const soc = hourlySoc.length > 0
            ? hourlySoc.map(h => h.soc_pct)
            : [50, 56, 62, 68, 72, 72, 70, 68, 64, 60, 58, 55, 52, 48, 42, 34, 26, 20, 18, 16, 16, 20, 32, 50];

        const traceSoc = {
            x: hours,
            y: soc,
            name: 'Battery SoC (%)',
            type: 'scatter',
            mode: 'lines+markers',
            fill: 'tozeroy',
            fillcolor: 'rgba(124, 58, 237, 0.12)',
            line: { width: 2.5, color: this.colors.purple }
        };
        const traceMax = {
            x: hours,
            y: Array(hours.length).fill(95),
            name: 'Max SoC (95%)',
            type: 'scatter',
            mode: 'lines',
            line: { color: this.colors.red, dash: 'dash', width: 1.5 }
        };
        const traceMin = {
            x: hours,
            y: Array(hours.length).fill(15),
            name: 'Min SoC Protection (15%)',
            type: 'scatter',
            mode: 'lines',
            line: { color: this.colors.amber, dash: 'dash', width: 1.5 }
        };

        const layout = this.getBaseLayout({
            title: { text: '24-Hour Battery SoC Trajectory (1,000 kWh Capacity)', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'State of Charge (%)', range: [0, 100] }
        });

        Plotly.newPlot(el, [traceSoc, traceMax, traceMin], layout, this.baseConfig);
    },

    async renderBatteryChargeDischarge(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const battData = await this.fetchBatteryData();
        const chargeKw = battData?.hourly_charge_kw || [0,0,0,0,0,0,0,0,80,140,210,230,190,140,0,0,0,0,0,0,0,0,0,0];
        const dischargeKw = (battData?.hourly_discharge_kw || [0,0,0,0,0,0,0,0,0,0,0,0,0,0,60,110,180,240,260,210,140,80,0,0]).map(v => -v);
        const hours = battData?.hourly_soc?.map(h => h.hour_label) || this.hours24;

        const traceCharge = {
            x: hours,
            y: chargeKw,
            name: 'BESS Charging (kW)',
            type: 'bar',
            marker: { color: this.colors.primaryGreen }
        };
        const traceDischarge = {
            x: hours,
            y: dischargeKw,
            name: 'BESS Discharging (kW)',
            type: 'bar',
            marker: { color: this.colors.purple }
        };

        const layout = this.getBaseLayout({
            title: { text: '24-Hour Battery Dispatch Power Envelope (kW)', font: { size: 13, color: this.colors.heading } },
            barmode: 'relative',
            yaxis: { title: 'Discharge (-) / Charge (+) in kW' }
        });

        Plotly.newPlot(el, [traceCharge, traceDischarge], layout, this.baseConfig);
    },

    async renderBatteryUtilization(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const battData = await this.fetchBatteryData();
        const chargeKw = battData?.hourly_charge_kw || [];
        const dischargeKw = battData?.hourly_discharge_kw || [];
        const hours = battData?.hourly_soc?.map(h => h.hour_label) || this.hours24;

        const hourlyThroughput = hours.map((_, i) => roundVal((chargeKw[i] || 0) + (dischargeKw[i] || 0)));

        function roundVal(v) { return Math.round(v * 10) / 10; }

        const trace = {
            x: hours,
            y: hourlyThroughput,
            name: 'BESS Throughput (kWh)',
            type: 'bar',
            marker: { color: this.colors.secondaryTeal }
        };

        const layout = this.getBaseLayout({
            title: { text: 'Hourly BESS Energy Throughput & Cycling Intensity (kWh)', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Hourly Throughput (kWh)' }
        });

        Plotly.newPlot(el, [trace], layout, this.baseConfig);
    },

    // Solar Page Charts
    renderSolarHourlyYield(containerId) {
        this.renderSolarUncertaintyDistribution(containerId);
    },
    renderSolarVsCampusDemand(containerId) {
        this.renderOverviewSolarVsDemand(containerId);
    },
    renderSolarWeatherScenarios(containerId) {
        this.renderSolarByWeatherCondition(containerId);
    },

    // Cost & Savings Page Charts
    async renderCostsStochasticVsDeterministic(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const costData = await this.fetchCostData();
        const comp = costData?.hourly_comparison || [];
        const hours = comp.length > 0 ? comp.map(h => h.hour_label) : this.hours24;
        const stochasticINR = comp.length > 0 ? comp.map(h => h.rp_hourly_cost_inr) : [966, 903, 882, 861, 903, 1092, 2700, 3900, 5400, 6300, 6675, 6862, 6525, 6450, 10738, 10915, 10384, 8732, 7316, 6372, 3450, 2925, 1302, 1092];
        const deterministicINR = comp.length > 0 ? comp.map(h => h.eev_hourly_cost_inr) : stochasticINR.map(v => Math.round(v * 1.05));

        const traces = [
            {
                x: hours,
                y: stochasticINR,
                name: 'Stochastic Schedule RP (INR)',
                type: 'scatter',
                mode: 'lines+markers',
                marker: { size: 4 },
                line: { width: 2.5, color: this.colors.primaryGreen }
            },
            {
                x: hours,
                y: deterministicINR,
                name: 'Deterministic Baseline EEV (INR)',
                type: 'scatter',
                mode: 'lines',
                line: { width: 2, color: this.colors.red, dash: 'dash' }
            }
        ];

        const layout = this.getBaseLayout({
            title: { text: 'Hourly Energy Procurement: Stochastic (RP) vs. Deterministic (EEV) in INR', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Hourly Expected Spend (INR)' }
        });

        Plotly.newPlot(el, traces, layout, this.baseConfig);
    },

    async renderCostsDailySpend(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const costData = await this.fetchCostData();
        const tou = costData?.tou_spend_breakdown || {};
        const offPeakSpend = tou.off_peak?.spend_inr || 12600;
        const normalSpend = tou.normal?.spend_inr || 38400;
        const peakSpend = tou.peak?.spend_inr || 18540;

        const trace = {
            values: [offPeakSpend, normalSpend, peakSpend],
            labels: ['Off-Peak Window (₹4.20/kWh)', 'Normal Window (₹7.50/kWh)', 'Peak Window (₹11.80/kWh)'],
            type: 'pie',
            hole: 0.5,
            marker: {
                colors: [this.colors.blue, this.colors.secondaryTeal, this.colors.red]
            }
        };

        const layout = {
            ...this.getBaseLayout(),
            title: { text: 'Daily Energy Spend Share by TOU Tariff Window (INR)', font: { size: 13, color: this.colors.heading } },
            showlegend: true,
            margin: { t: 30, r: 20, l: 20, b: 20 }
        };

        Plotly.newPlot(el, [trace], layout, this.baseConfig);
    },

    async renderCostsBreakdown(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const costData = await this.fetchCostData();
        const comp = costData?.component_breakdown || {};
        const daCost = comp.day_ahead_procurement_inr || 26162.75;
        const rtCost = comp.expected_real_time_balancing_inr || 43378.00;
        const bessCost = comp.bess_cycling_cost_inr || 147.20;
        const exportRev = comp.export_credit_inr || 0.0;

        const trace = {
            x: ['Day-Ahead Grid Import', 'Expected Real-Time Balancing', 'BESS Cycling Cost', 'Surplus Export Credit'],
            y: [daCost, rtCost, bessCost, -exportRev],
            type: 'bar',
            marker: {
                color: [this.colors.blue, this.colors.amber, this.colors.purple, this.colors.primaryGreen]
            }
        };

        const layout = this.getBaseLayout({
            title: { text: 'Microgrid Net Daily Cost Ledger Components (INR)', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Cost (+) / Credit (-) in INR' }
        });

        Plotly.newPlot(el, [trace], layout, this.baseConfig);
    },

    async renderCostsSavingsComparison(containerId) {
        const el = document.getElementById(containerId);
        if (!el || !window.Plotly) return;

        const costData = await this.fetchCostData();
        const dailyVSS = costData?.metrics?.vss_daily_savings_inr || 1140.89;

        const days = Array.from({ length: 30 }, (_, i) => `Day ${i + 1}`);
        let cumulative = 0;
        const cumulativeSavings = days.map(() => {
            cumulative += dailyVSS;
            return Math.round(cumulative);
        });

        const trace = {
            x: days,
            y: cumulativeSavings,
            name: 'Cumulative Stochastic Savings (VSS)',
            type: 'scatter',
            mode: 'lines',
            fill: 'tozeroy',
            fillcolor: 'rgba(22, 163, 74, 0.15)',
            line: { width: 2.5, color: this.colors.primaryGreen }
        };

        const layout = this.getBaseLayout({
            title: { text: '30-Day Cumulative Stochastic Benefit Projection (VSS in INR)', font: { size: 13, color: this.colors.heading } },
            yaxis: { title: 'Cumulative Savings (INR)' }
        });

        Plotly.newPlot(el, [trace], layout, this.baseConfig);
    }
};

window.GridWiseCharts = GridWiseCharts;

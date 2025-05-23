// Chart colors
const chartColors = {
    primary: '#4e73df',
    success: '#1cc88a',
    info: '#36b9cc',
    warning: '#f6c23e',
    danger: '#e74a3b',
    secondary: '#858796',
    light: '#f8f9fc',
    dark: '#5a5c69'
};

// Chart instances for updating
let sectorChart = null;
let assetChart = null;
let performanceChart = null;
let riskChart = null;

// Initialize charts when the page loads
document.addEventListener('DOMContentLoaded', function() {
    fetchPortfolioAnalytics();
    // Set up auto-refresh every 5 minutes
    setInterval(fetchPortfolioAnalytics, 300000);
});

// Fetch portfolio analytics data
async function fetchPortfolioAnalytics() {
    try {
        const response = await fetch('/api/portfolio/analytics');
        const data = await response.json();
        
        updateMetrics(data.metrics);
        renderSectorAllocation(data.sectorAllocation);
        renderAssetClassDistribution(data.assetClassDistribution);
        renderPerformanceChart(data.performance);
        renderRiskMetrics(data.riskMetrics);

        // Show success toast
        showToast('Data refreshed successfully', 'success');
    } catch (error) {
        console.error('Error fetching portfolio analytics:', error);
        showToast('Error refreshing data', 'error');
    }
}

// Update metric cards with animation
function updateMetrics(metrics) {
    animateValue('totalValue', metrics.totalValue, formatCurrency);
    animateValue('dailyPnL', metrics.dailyPnL, formatCurrency);
    animateValue('sharpeRatio', metrics.sharpeRatio, (v) => v.toFixed(2));
    animateValue('beta', metrics.beta, (v) => v.toFixed(2));
}

// Animate value changes
function animateValue(elementId, end, formatter) {
    const element = document.getElementById(elementId);
    const start = parseFloat(element.textContent.replace(/[^0-9.-]+/g, '')) || 0;
    const duration = 1000;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        const current = start + (end - start) * progress;
        element.textContent = formatter(current);

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

// Render sector allocation chart
function renderSectorAllocation(data) {
    const ctx = document.getElementById('sectorAllocationChart').getContext('2d');
    
    if (sectorChart) {
        sectorChart.destroy();
    }

    sectorChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.values,
                backgroundColor: Object.values(chartColors),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        padding: 20,
                        font: {
                            size: 12
                        }
                    }
                },
                title: {
                    display: true,
                    text: 'Portfolio Sector Allocation',
                    font: {
                        size: 16
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.raw.toFixed(2)}%`;
                        }
                    }
                }
            },
            animation: {
                animateScale: true,
                animateRotate: true
            }
        }
    });
}

// Render asset class distribution chart
function renderAssetClassDistribution(data) {
    const ctx = document.getElementById('assetClassChart').getContext('2d');
    
    if (assetChart) {
        assetChart.destroy();
    }

    assetChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.values,
                backgroundColor: Object.values(chartColors),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        padding: 20,
                        font: {
                            size: 12
                        }
                    }
                },
                title: {
                    display: true,
                    text: 'Asset Class Distribution',
                    font: {
                        size: 16
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.raw.toFixed(2)}%`;
                        }
                    }
                }
            },
            animation: {
                animateScale: true,
                animateRotate: true
            }
        }
    });
}

// Render performance chart
function renderPerformanceChart(data) {
    const ctx = document.getElementById('performanceChart').getContext('2d');
    
    if (performanceChart) {
        performanceChart.destroy();
    }

    performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: [
                {
                    label: 'Portfolio',
                    data: data.portfolioValues,
                    borderColor: chartColors.primary,
                    backgroundColor: 'rgba(78, 115, 223, 0.1)',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Benchmark (Nifty 50)',
                    data: data.benchmarkValues,
                    borderColor: chartColors.secondary,
                    backgroundColor: 'rgba(133, 135, 150, 0.1)',
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Portfolio Performance vs Benchmark',
                    font: {
                        size: 16
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${formatCurrency(context.raw)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

// Render risk metrics chart
function renderRiskMetrics(data) {
    const ctx = document.getElementById('riskMetricsChart').getContext('2d');
    
    if (riskChart) {
        riskChart.destroy();
    }

    riskChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Volatility', 'Beta', 'Sharpe Ratio', 'Alpha', 'Information Ratio'],
            datasets: [{
                label: 'Portfolio Metrics',
                data: [
                    data.volatility,
                    data.beta,
                    data.sharpeRatio,
                    data.alpha,
                    data.informationRatio
                ],
                backgroundColor: 'rgba(78, 115, 223, 0.2)',
                borderColor: chartColors.primary,
                pointBackgroundColor: chartColors.primary,
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: chartColors.primary
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Risk Metrics Overview',
                    font: {
                        size: 16
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.raw.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                r: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 0.5
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            }
        }
    });
}

// Utility function to format currency
function formatCurrency(value) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value);
}

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    document.body.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        document.body.removeChild(toast);
    });
} 
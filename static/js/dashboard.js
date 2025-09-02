function initDashboard() {
    console.info("initDashboard Start")

    // 定义图表实例存储对象
    const chartInstances = {
        projectTaskChart: null,
        userTaskChart: null,
        zoomedChart: null
    };

    // 定义刷新函数
    function refreshProjectChart() {
        console.log("Refreshing project chart...");
        if (chartInstances.projectTaskChart) {
            chartInstances.projectTaskChart.destroy();
            chartInstances.projectTaskChart = null;
        }
        initProjectTaskChart();
    }

    function refreshUserChart() {
        console.log("Refreshing user chart...");
        if (chartInstances.userTaskChart) {
            chartInstances.userTaskChart.destroy();
            chartInstances.userTaskChart = null;
        }
        initUserTaskChart();
    }

    // 全局刷新函数
    function refreshDashboard() {
        console.log("Refreshing dashboard...");
        refreshProjectChart();
        refreshUserChart();
        fetchStats();
    }

    // 获取统计数据
    async function fetchStats() {
        try {
            const [totalProjects, totalTasks, activeProjects, delayedTasks] = await Promise.all([
                fetchStat('/api/dashboard/total-projects', 'total'),
                fetchStat('/api/dashboard/total-tasks', 'total'),
                fetchStat('/api/dashboard/active-projects', 'active'),
                fetchStat('/api/dashboard/delayed-tasks', 'delayed')
            ]);
            
            document.getElementById('totalProjects').textContent = totalProjects;
            document.getElementById('totalTasks').textContent = totalTasks;
            document.getElementById('activeProjects').textContent = activeProjects;
            document.getElementById('delayedTasks').textContent = delayedTasks;
        } catch (error) {
            console.error('Failed to fetch stats:', error);
        }
    }

    async function fetchStat(url, key) {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Failed to fetch stat: ${response.status}`);
            }
            const data = await response.json();
            return data[key];
        } catch (error) {
            console.error(`Error fetching stat from ${url}:`, error);
            return '--';
        }
    }
    
    // 颜色方案 - 专业美观
    const COLORS = {
        primary: '#4e73df',
        success: '#1cc88a',
        info: '#36b9cc',
        warning: '#f6c23e',
        danger: '#e74a3b',
        secondary: '#858796',
        dark: '#5a5c69',
        light: '#f8f9fc'
    };
    
    // 获取项目任务数量
    async function fetchProjectTaskCounts() {
        try {
            const response = await fetch('/api/dashboard/project-task-counts');
            if (!response.ok) {
                throw new Error(`Failed to fetch project task counts: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching project task counts:', error);
            throw error;
        }
    }
    
    // 获取用户任务分布
    async function fetchUserTaskDistribution() {
        try {
            const response = await fetch('/api/dashboard/user-task-distribution');
            if (!response.ok) {
                throw new Error(`Failed to fetch user task distribution: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching user task distribution:', error);
            throw error;
        }
    }
    
    // 初始化项目任务数量柱状图
    async function initProjectTaskChart() {
        try {
            const ctx = document.getElementById('projectTaskChart');
            if (!ctx) return;
            
            // 销毁现有图表
            if (chartInstances.projectTaskChart) {
                chartInstances.projectTaskChart.destroy();
            }
            
            // 获取数据
            const data = await fetchProjectTaskCounts();
            // console.info("projectTaskCounts: ", data);
            
            // 提取项目和任务数量
            const labels = data.map(item => item.project_name || `Project ${item.project_id}`);
            const counts = data.map(item => item.task_count);
            
            // 创建渐变色
            const ctx2d = ctx.getContext('2d');
            const gradient = ctx2d.createLinearGradient(0, 0, 0, 400);
            gradient.addColorStop(0, 'rgba(78, 115, 223, 0.85)');
            gradient.addColorStop(1, 'rgba(78, 115, 223, 0.1)');
            
            chartInstances.projectTaskChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Number of Tasks',
                        data: counts,
                        backgroundColor: gradient,
                        borderColor: COLORS.primary,
                        borderWidth: 1,
                        borderRadius: 8,
                        barPercentage: 0.6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            backgroundColor: 'rgba(255, 255, 255, 0.95)',
                            titleColor: COLORS.dark,
                            bodyColor: COLORS.secondary,
                            borderColor: '#e3e6f0',
                            borderWidth: 1,
                            padding: 12,
                            cornerRadius: 8,
                            displayColors: false,
                            callbacks: {
                                label: function(context) {
                                    return `${context.raw} tasks`;
                                },
                                title: function(context) {
                                    return context[0].label;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                display: false,
                                drawBorder: false
                            },
                            ticks: {
                                color: COLORS.secondary,
                                maxRotation: 45,
                                minRotation: 45
                            }
                        },
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.04)',
                                drawBorder: false
                            },
                            ticks: {
                                color: COLORS.secondary,
                                padding: 10,
                                callback: function(value) {
                                    if (value % 1 === 0) return value;
                                }
                            },
                            title: {
                                display: true,
                                text: 'Number of Tasks',
                                color: COLORS.dark,
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                }
                            }
                        }
                    },
                    animation: {
                        duration: 2000,
                        easing: 'easeOutQuart'
                    }
                }
            });
            
        } catch (error) {
            console.error('Error initializing project task chart:', error);
            const errorMsg = 'Failed to load project task data';
            document.getElementById('projectTaskChartContainer').innerHTML = 
                `<div class="chart-error">${errorMsg}</div>`;
        }
    }
    
    // 初始化用户任务分布饼图
    async function initUserTaskChart() {
        try {
            const ctx = document.getElementById('userTaskChart');
            if (!ctx) return;
            
            // 销毁现有图表
            if (chartInstances.userTaskChart) {
                chartInstances.userTaskChart.destroy();
            }
            
            // 获取数据
            const data = await fetchUserTaskDistribution();
            // console.info("userTaskDistribution: ", data);
            
            // 提取用户和任务数量
            const labels = data.map(item => item.full_name || `User ${item.user_id}`);
            const counts = data.map(item => item.task_count);
            
            // 使用预定义颜色方案
            const backgroundColors = [
                COLORS.primary,
                COLORS.success,
                COLORS.info,
                COLORS.warning,
                COLORS.danger,
                COLORS.secondary,
                '#6f42c1',
                '#20c997',
                '#fd7e14',
                '#6610f2'
            ];
            
            chartInstances.userTaskChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: counts,
                        backgroundColor: backgroundColors,
                        borderColor: '#fff',
                        borderWidth: 2,
                        hoverOffset: 15
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                padding: 15,
                                font: {
                                    size: 13
                                },
                                usePointStyle: true,
                                pointStyle: 'circle',
                                color: COLORS.dark
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(255, 255, 255, 0.95)',
                            titleColor: COLORS.dark,
                            bodyColor: COLORS.secondary,
                            borderColor: '#e3e6f0',
                            borderWidth: 1,
                            padding: 12,
                            cornerRadius: 8,
                            displayColors: true,
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = context.chart.getDatasetMeta(0).total;
                                    const percentage = Math.round((value / total) * 100);
                                    return `${label}: ${value} tasks (${percentage}%)`;
                                }
                            }
                        }
                    },
                    animation: {
                        animateRotate: true,
                        animateScale: true,
                        duration: 2000
                    }
                }
            });
            
        } catch (error) {
            console.error('Error initializing user task chart:', error);
            const errorMsg = 'Failed to load user task data';
            document.getElementById('userTaskChartContainer').innerHTML = 
                `<div class="chart-error">${errorMsg}</div>`;
        }
    }
    
    // 窗口大小调整时重新渲染图表
    let resizeTimer;
    function handleResize() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            refreshProjectChart();
            refreshUserChart();
        }, 500);
    }
    
    // 初始化仪表板
    function init() {
        console.info("Init dashboard");
        // 确保Chart.js已加载
        if (typeof Chart === 'undefined') {
            console.error('Chart.js is not loaded');
            document.getElementById('projectTaskChartContainer').innerHTML = 
                '<div class="chart-error">Chart library not loaded</div>';
            document.getElementById('userTaskChartContainer').innerHTML = 
                '<div class="chart-error">Chart library not loaded</div>';
            return;
        }
        
        // 初始化图表
        initProjectTaskChart();
        initUserTaskChart();
        
        // 获取并更新统计数据
        fetchStats();
        
        // 添加窗口大小调整事件监听器
        window.addEventListener('resize', handleResize);
        
        // 添加全局刷新按钮事件
        document.getElementById('refreshDashboardBtn')?.addEventListener('click', refreshDashboard);
    }
    
    window.refreshProjectChart = refreshProjectChart;
    window.refreshUserChart = refreshUserChart;
    window.refreshDashboard = refreshDashboard;
    
    init();
}
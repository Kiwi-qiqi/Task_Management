/**
 * Initializes the task management system
 * Sets up event listeners, loads initial data, and manages application state
 */
function initTaskManagement() {
    console.info("Initializing Task Management System");
    
    // Application state variables
    let tasks = []; // Stores all loaded tasks
    let currentSortField = 'title'; // Current sorting field
    let currentSortDirection = 'asc'; // Current sorting direction
    let selectedTaskId = null; // Currently selected task ID
    let detailVisible = false; // Flag for task detail visibility
    let isEditing = false; // Flag to track if we're in edit mode

    // Load initial data
    loadUsers();
    loadProjects();
    loadTasks();
    
    // Setup event listeners
    setupEventListeners();
    
    // Set up table sorting
    setupSorting();
    
    /**
     * Loads users from API and populates dropdowns
     */
    function loadUsers() {
        fetch('/api/users')
            .then(response => {
                if (!response.ok) throw new Error(`Failed to load users: ${response.status}`);
                return response.json();
            })
            .then(users => {
                populateDropdown('assigneeFilter', users, 'full_name', 'username');
                populateDropdown('assigneeSelect', users, 'full_name', 'username');
                populateDropdown('editAssignee', users, 'full_name', 'username');
            })
            .catch(error => {
                console.error('Error loading users:', error);
                showErrorNotification('Failed to load users. Please try again later.');
            });
    }

    /**
     * Loads projects from API and populates dropdowns
     */
    function loadProjects() {
        fetch('/api/projects')
            .then(response => {
                if (!response.ok) throw new Error(`Failed to load projects: ${response.status}`);
                return response.json();
            })
            .then(projects => {
                populateDropdown('projectFilter', projects, 'name');
                populateDropdown('projectSelect', projects, 'name');
                populateDropdown('editProject', projects, 'name');
            })
            .catch(error => {
                console.error('Error loading projects:', error);
                showErrorNotification('Failed to load projects. Please try again later.');
            });
    }

    /**
     * Populates dropdown with items
     * @param {string} elementId - ID of dropdown element
     * @param {Array} items - Items to populate
     * @param {string} primaryField - Primary display field
     * @param {string} [fallbackField] - Fallback display field
     */
    function populateDropdown(elementId, items, primaryField, fallbackField = null) {
        const dropdown = document.getElementById(elementId);
        if (!dropdown) {
            console.warn(`Dropdown not found: ${elementId}`);
            return;
        }
        
        // Clear existing options (keep first placeholder)
        while (dropdown.options.length > 1) dropdown.remove(1);
        
        // Add new options
        items.forEach(item => {
            const option = document.createElement('option');
            option.value = item.id;
            option.textContent = item[primaryField] || 
                                (fallbackField && item[fallbackField]) || 
                                `Item ${item.id}`;
            dropdown.appendChild(option);
        });
    }

    /**
     * Loads tasks from API with current filters
     */
    function loadTasks() {
        const params = new URLSearchParams();
        const status = document.getElementById('statusFilter')?.value;
        const assignee = document.getElementById('assigneeFilter')?.value;
        const project = document.getElementById('projectFilter')?.value;
        const priority = document.getElementById('priorityFilter')?.value;
        const text = document.getElementById('textSearch')?.value;
        
        // Add filter parameters
        if (status && status !== 'all') params.append('status', status);
        if (assignee && assignee !== 'all') params.append('assignee', assignee);
        if (project && project !== 'all') params.append('project', project);
        if (priority && priority !== 'all') params.append('priority', priority);
        if (text) params.append('search_text', text);
        
        fetch(`/api/tasks?${params.toString()}`)
            .then(response => {
                if (!response.ok) throw new Error(`Failed to load tasks: ${response.status}`);
                return response.json();
            })
            .then(data => {
                tasks = data.tasks || data; // Handle different API formats
                sortTasks();
                renderTasksTable(tasks);
            })
            .catch(error => {
                console.error('Error loading tasks:', error);
                showErrorNotification('Failed to load tasks. Please try again later.');
                renderTasksTable([]); // 显示空状态
            });
    }

    /**
     * Renders tasks in the table
     * @param {Array} tasks - Tasks to render
     */
    function renderTasksTable(tasks) {
        const tableBody = document.getElementById('tasksTableBody');
        const tasksCount = document.getElementById('tasksCount');
        if (!tableBody || !tasksCount) return;
        
        tableBody.innerHTML = ''; // Clear existing rows
        tasksCount.textContent = tasks.length; // Update count
        
        // Handle empty state
        if (tasks.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-5">
                        <div class="empty-state">
                            <i class="bi bi-inbox"></i>
                            <h4>No tasks found</h4>
                            <p>Try adjusting your search criteria</p>
                        </div>
                    </td>
                </tr>`;
            return;
        }
        
        // Render each task
        tasks.forEach(task => {
            const row = document.createElement('tr');
            row.dataset.taskId = task.id;
            
            // Add selected class if this is the current task
            if (selectedTaskId === task.id && detailVisible) {
                row.classList.add('selected');
            }
            
            // Safely handle data
            const projectName = task.project?.name || 'No Project';
            const assigneeName = task.assignee?.full_name || task.assignee?.username || 'Unassigned';
            const dueDate = task.due_date ? formatDate(task.due_date) : 'Not set';
            const priorityClass = getPriorityClass(task.priority);
            const priorityText = getPriorityText(task.priority);
            const statusClass = getStatusClass(task.status);
            const statusText = getStatusText(task.status);
            
            row.innerHTML = `
                <td>${task.title || 'Untitled Task'}</td>
                <td>${projectName}</td>
                <td>${assigneeName}</td>
                <td>
                    <span class="priority-indicator ${priorityClass}"></span>
                    ${priorityText}
                </td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td>${dueDate}</td>
            `;
            
            tableBody.appendChild(row);
        });
    }

    /**
     * Formats date to YYYY-MM-DD (Beijing time)
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date
     */
    function formatDate(dateString) {
        if (!dateString) return 'Not set';
        try {
            const date = new Date(dateString);
            const beijingDate = new Date(date.getTime() + 8 * 60 * 60 * 1000);
            const year = beijingDate.getUTCFullYear();
            const month = String(beijingDate.getUTCMonth() + 1).padStart(2, '0');
            const day = String(beijingDate.getUTCDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        } catch (e) {
            return 'Invalid date';
        }
    }

    /**
     * Formats date for datetime-local input (Beijing time)
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted datetime string
     */
    function formatDateTimeForInput(dateString) {
        if (!dateString) return '';
        try {
            const date = new Date(dateString);
            const beijingTime = date.getTime() + 8 * 60 * 60 * 1000;
            const beijingDate = new Date(beijingTime);
            const year = beijingDate.getUTCFullYear();
            const month = String(beijingDate.getUTCMonth() + 1).padStart(2, '0');
            const day = String(beijingDate.getUTCDate()).padStart(2, '0');
            const hours = String(beijingDate.getUTCHours()).padStart(2, '0');
            const minutes = String(beijingDate.getUTCMinutes()).padStart(2, '0');
            return `${year}-${month}-${day}T${hours}:${minutes}`;
        } catch (e) {
            console.warn('Invalid date format', dateString);
            return '';
        }
    }

    // Priority helper functions
    function getPriorityClass(priority) {
        const p = (priority || '').toLowerCase();
        return {
            high: 'priority-high',
            medium: 'priority-medium',
            low: 'priority-low',
            urgent: 'priority-urgent'
        }[p] || 'priority-unknown';
    }

    function getPriorityText(priority) {
        const p = (priority || '').toLowerCase();
        return {
            high: 'High',
            medium: 'Medium',
            low: 'Low',
            urgent: 'Urgent'
        }[p] || 'Unknown';
    }

    // Status helper functions
    function getStatusClass(status) {
        const s = (status || '').toLowerCase();
        return {
            todo: 'status-todo',
            in_progress: 'status-in_progress',
            review: 'status-review',
            done: 'status-done'
        }[s] || 'status-unknown';
    }

    function getStatusText(status) {
        const s = (status || '').toLowerCase();
        return {
            todo: 'To Do',
            in_progress: 'In Progress',
            review: 'In Review',
            done: 'Done'
        }[s] || 'Unknown';
    }

    // 修改了任务详情加载函数，添加数据验证
    function loadTaskDetails(taskId) {
        const task = tasks.find(t => t.id === taskId);
        if (!task) return;
        
        const container = document.getElementById('taskDetailContainer');
        if (!container) return;
        
        container.style.display = 'block';
        
        // 设置任务详情
        document.getElementById('taskDetailTitle').textContent = task.title || 'Untitled Task';
        
        // 设置状态和优先级徽章
        document.getElementById('taskDetailStatus').className = `status-badge ${getStatusClass(task.status)}`;
        document.getElementById('taskDetailStatus').textContent = getStatusText(task.status);
        document.getElementById('taskDetailPriority').className = `badge ${getPriorityClass(task.priority)}`;
        document.getElementById('taskDetailPriority').textContent = getPriorityText(task.priority);
        
        // 格式化日期函数
        const formatDate = (dateString) => {
            if (!dateString) return 'Not set';
            try {
                const date = new Date(dateString);
                return date.toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                });
            } catch (e) {
                return 'Invalid date';
            }
        };
        
        // 安全设置其他详情
        document.getElementById('taskDetailDescription').textContent = task.description || 'No description provided';
        document.getElementById('taskDetailType').textContent = task.type ? 
            task.type.charAt(0).toUpperCase() + task.type.slice(1) : 'Unknown';
            
        document.getElementById('taskDetailSeverity').textContent = task.severity ? 
            task.severity.charAt(0).toUpperCase() + task.severity.slice(1) : 'Unknown';
            
        document.getElementById('taskDetailCreated').textContent = formatDate(task.created_at);
        document.getElementById('taskDetailUpdated').textContent = formatDate(task.updated_at);
        
        // 安全处理项目信息
        const projectName = task.project?.name || 'No Project';
        const categoryName = task.project?.category?.name || 'No Category';
        const categoryType = task.project?.category?.type || '';
        
        document.getElementById('taskDetailProject').textContent = projectName;
        document.getElementById('taskDetailCategory').textContent = `${categoryName}${categoryType ? ` (${categoryType})` : ''}`;
        
        // 安全处理分配人信息
        const assigneeName = task.assignee?.full_name || task.assignee?.username || 'Unassigned';
        document.getElementById('taskDetailAssignee').textContent = assigneeName;
        
        document.getElementById('taskDetailStartDate').textContent = formatDate(task.start_date);
        document.getElementById('taskDetailDueDate').textContent = formatDate(task.due_date);
    }

    // 修改了评论加载函数
    function loadComments(taskId) {
        fetch(`/api/tasks/${taskId}/comments`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Failed to load comments: ${response.status}`);
                }
                return response.json();
            })
            .then(comments => {
                renderComments(comments);
            })
            .catch(error => {
                console.error('Error loading comments:', error);
                renderComments([]); // 显示空状态
            });
    }

    // 修改了评论渲染函数
    function renderComments(comments) {
        const container = document.getElementById('commentsContainer');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (!comments || comments.length === 0) {
            container.innerHTML = '<p class="text-muted">No comments yet</p>';
            return;
        }
        
        comments.forEach(comment => {
            const commentCard = document.createElement('div');
            commentCard.className = 'comment-card';
            
            // 格式化日期
            let formattedDate = 'Unknown date';
            try {
                const date = new Date(comment.created_at);
                formattedDate = date.toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            } catch (e) {
                console.warn('Invalid date format for comment', comment);
            }
            
            // 安全处理作者信息
            const authorName = comment.author?.full_name || 
                              comment.author?.username || 
                              'Unknown User';
            
            commentCard.innerHTML = `
                <div class="comment-header">
                    <div class="comment-author">${authorName}</div>
                    <div class="comment-date">${formattedDate}</div>
                </div>
                <div class="comment-content">${comment.content || 'No content'}</div>
            `;
            
            container.appendChild(commentCard);
        });
    }

    /**
     * Sets up event listeners for UI interactions
     */
    function setupEventListeners() {
        const tableBody = document.getElementById('tasksTableBody');
        if (tableBody) tableBody.addEventListener('click', handleTaskRowClick);
        
        // Filter change listeners
        ['statusFilter', 'assigneeFilter', 'projectFilter', 'priorityFilter'].forEach(id => {
            const filter = document.getElementById(id);
            if (filter) filter.addEventListener('change', loadTasks);
        });
        
        // Search input listener
        const textSearch = document.getElementById('textSearch');
        if (textSearch) textSearch.addEventListener('input', debounce(loadTasks, 300));
        
        // Reset filters
        const resetBtn = document.getElementById('resetFilters');
        if (resetBtn) resetBtn.addEventListener('click', resetFilters);
        
        // Unified task modal handlers
        document.getElementById('createTaskBtn').addEventListener('click', () => openTaskModal());
        document.getElementById('editTaskBtn').addEventListener('click', () => openTaskModal(selectedTaskId));
        
        // Task form submission
        document.getElementById('submitTaskForm').addEventListener('click', handleTaskSubmission);
        
        // Close detail panel
        document.getElementById('closeDetailBtn').addEventListener('click', closeTaskDetail);
        
        // Add comment form
        document.getElementById('addCommentForm').addEventListener('submit', function(e) {
            e.preventDefault();
            addComment();
        });
    }


    function closeTaskDetail() {
        const scrollContainer = document.getElementById('tasksScrollContainer');
        const taskDetailContainer = document.getElementById('taskDetailContainer');
        
        // 更新滚动容器高度
        if (scrollContainer) {
            scrollContainer.style.maxHeight = '70vh';
        }
        
        // 隐藏任务详情容器
        if (taskDetailContainer) {
            taskDetailContainer.style.display = 'none';
        }
        
        // 移除选中行的选中类
        if (selectedTaskId) {
            const selectedRow = document.querySelector(`#tasksTableBody tr[data-task-id="${selectedTaskId}"]`);
            if (selectedRow) {
                selectedRow.classList.remove('selected');
            }
        }
        
        // 重置状态
        detailVisible = false;
        selectedTaskId = null;
    }
    // 任务行点击处理
    function handleTaskRowClick(e) {
        const row = e.target.closest('tr');
        if (!row || !row.dataset.taskId) return;
        
        const taskId = parseInt(row.dataset.taskId);
        const scrollContainer = document.getElementById('tasksScrollContainer');
        
        // 如果点击的是已选中的任务行，则切换详情显示状态
        if (selectedTaskId === taskId) {
            detailVisible = !detailVisible;
            
            if (detailVisible) {
                // 显示详情
                if (scrollContainer) scrollContainer.style.maxHeight = '40vh';
                document.getElementById('taskDetailContainer').style.display = 'block';
                row.classList.add('selected');
            } else {
                // 隐藏详情
                if (scrollContainer) scrollContainer.style.maxHeight = '70vh';
                document.getElementById('taskDetailContainer').style.display = 'none';
                row.classList.remove('selected');
            }
        } else {
            // 否则选中新任务并显示详情
            selectedTaskId = taskId;
            detailVisible = true;
            
            // 从所有行中移除选中类
            document.querySelectorAll('#tasksTableBody tr').forEach(r => {
                r.classList.remove('selected');
            });
            
            // 向点击的行添加选中类
            row.classList.add('selected');
            
            // 加载任务详情
            loadTaskDetails(taskId);
            
            // 加载评论
            loadComments(taskId);
            
            // 更新滚动容器高度
            if (scrollContainer) scrollContainer.style.maxHeight = '40vh';
            document.getElementById('taskDetailContainer').style.display = 'block';
        }
    }

    // 其他辅助函数
    function resetFilters() {
        document.getElementById('statusFilter').value = 'all';
        document.getElementById('assigneeFilter').value = 'all';
        document.getElementById('projectFilter').value = 'all';
        document.getElementById('priorityFilter').value = 'all';
        document.getElementById('textSearch').value = '';
        loadTasks();
    }

    function debounce(func, wait) {
        let timeout;
        return function() {
            const context = this;
            const args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), wait);
        };
    }

    function showErrorNotification(message) {
        // 在实际应用中，这里可以显示一个美观的错误通知
        console.error('Error:', message);
        alert(message);
    }

    function loadTaskDetails(taskId) {
        const task = tasks.find(t => t.id === taskId);
        if (!task) return;
        
        const container = document.getElementById('taskDetailContainer');
        container.style.display = 'block';
        
        // 设置任务详情
        document.getElementById('taskDetailTitle').textContent = task.title;
        
        // 状态徽章
        let statusClass = '';
        let statusText = '';
        
        switch(task.status) {
            case 'todo':
                statusClass = 'status-todo';
                statusText = 'To Do';
                break;
            case 'in_progress':
                statusClass = 'status-in_progress';
                statusText = 'In Progress';
                break;
            case 'review':
                statusClass = 'status-review';
                statusText = 'In Review';
                break;
            case 'done':
                statusClass = 'status-done';
                statusText = 'Done';
                break;
        }
        
        document.getElementById('taskDetailStatus').className = `status-badge ${statusClass}`;
        document.getElementById('taskDetailStatus').textContent = statusText;
        
        // 优先级徽章
        let priorityClass = '';
        let priorityText = '';
        
        switch(task.priority) {
            case 'high':
                priorityClass = 'bg-danger';
                priorityText = 'High';
                break;
            case 'medium':
                priorityClass = 'bg-warning';
                priorityText = 'Medium';
                break;
            case 'low':
                priorityClass = 'bg-success';
                priorityText = 'Low';
                break;
            case 'urgent':
                priorityClass = 'bg-primary';
                priorityText = 'Urgent';
                break;
        }
        
        document.getElementById('taskDetailPriority').className = `badge ${priorityClass}`;
        document.getElementById('taskDetailPriority').textContent = priorityText;
        
        const formatDate = (dateString) => {
            if (!dateString) return 'Not set';
            
            // 创建Date对象并添加8小时转换为北京时间
            const date = new Date(dateString);
            const beijingDate = new Date(date.getTime() + 8 * 60 * 60 * 1000);
            
            // 提取北京时间的年月日
            const year = beijingDate.getUTCFullYear();
            const month = String(beijingDate.getUTCMonth() + 1).padStart(2, '0');
            const day = String(beijingDate.getUTCDate()).padStart(2, '0');
            
            return `${year}-${month}-${day}`;
        };
        
        // 设置其他详情
        document.getElementById('taskDetailDescription').textContent = task.description || 'No description provided';
        document.getElementById('taskDetailType').textContent = task.type.charAt(0).toUpperCase() + task.type.slice(1);
        document.getElementById('taskDetailSeverity').textContent = task.severity.charAt(0).toUpperCase() + task.severity.slice(1);
        document.getElementById('taskDetailCreated').textContent = formatDate(task.created_at);
        document.getElementById('taskDetailUpdated').textContent = formatDate(task.updated_at);
        document.getElementById('taskDetailProject').textContent = task.project.name;
        document.getElementById('taskDetailCategory').textContent = `${task.project.category.name} (${task.project.category.type})`;
        document.getElementById('taskDetailAssignee').textContent = task.assignee.full_name || task.assignee.username;
        document.getElementById('taskDetailStartDate').textContent = formatDate(task.start_date);
        document.getElementById('taskDetailDueDate').textContent = formatDate(task.due_date);
    }


    function loadComments(taskId) {
        fetch(`/api/tasks/${taskId}/comments`)
            .then(response => response.json())
            .then(comments => {
                renderComments(comments);
            })
            .catch(error => {
                console.error('Error loading comments:', error);
                alert('Failed to load comments. Please try again later.');
            });
    }

    function renderComments(comments) {
        const container = document.getElementById('commentsContainer');
        container.innerHTML = '';
        
        if (comments.length === 0) {
            container.innerHTML = '<p class="text-muted">No comments yet</p>';
            return;
        }
        
        comments.forEach(comment => {
            const commentCard = document.createElement('div');
            commentCard.className = 'comment-card';
            
            // 格式化日期
            const date = new Date(comment.created_at);
            const formattedDate = date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            
            commentCard.innerHTML = `
                <div class="comment-header">
                    <div class="comment-author">${comment.author.full_name || comment.author.username}</div>
                    <div class="comment-date">${formattedDate}</div>
                </div>
                <div class="comment-content">${comment.content}</div>
            `;
            
            container.appendChild(commentCard);
        });
    }

    
    // 设置表头排序功能
    function setupSorting() {
        document.querySelectorAll('.tasks-table th[data-sort]').forEach(th => {
            th.addEventListener('click', function() {
                const sortField = this.dataset.sort;
                
                // 如果点击的是当前排序字段，则切换方向
                if (sortField === currentSortField) {
                    currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
                } else {
                    // 否则设置新的排序字段，默认升序
                    currentSortField = sortField;
                    currentSortDirection = 'asc';
                }
                
                // 更新表头UI
                updateSortingUI();
                
                // 排序并重新渲染表格
                sortTasks();
                renderTasksTable(tasks);
            });
        });
    }
    
    // 任务排序
    function sortTasks() {
        tasks.sort((a, b) => {
            let valueA, valueB;
            
            switch(currentSortField) {
                case 'title':
                    valueA = a.title.toLowerCase();
                    valueB = b.title.toLowerCase();
                    break;
                case 'project':
                    valueA = a.project.name.toLowerCase();
                    valueB = b.project.name.toLowerCase();
                    break;
                case 'assignee':
                    valueA = (a.assignee.full_name || a.assignee.username).toLowerCase();
                    valueB = (b.assignee.full_name || b.assignee.username).toLowerCase();
                    break;
                case 'priority':
                    // 优先级排序权重
                    const priorityOrder = {urgent: 0, high: 1, medium: 2, low: 3};
                    valueA = priorityOrder[a.priority];
                    valueB = priorityOrder[b.priority];
                    break;
                case 'status':
                    // 状态排序权重
                    const statusOrder = {todo: 0, in_progress: 1, review: 2, done: 3};
                    valueA = statusOrder[a.status];
                    valueB = statusOrder[b.status];
                    break;
                case 'due_date':
                    valueA = a.due_date ? new Date(a.due_date) : new Date(0);
                    valueB = b.due_date ? new Date(b.due_date) : new Date(0);
                    break;
                default:
                    valueA = a.title.toLowerCase();
                    valueB = b.title.toLowerCase();
            }
            
            // 处理空值
            if (valueA === null || valueA === undefined) valueA = '';
            if (valueB === null || valueB === undefined) valueB = '';
            
            // 排序比较
            if (valueA < valueB) {
                return currentSortDirection === 'asc' ? -1 : 1;
            }
            if (valueA > valueB) {
                return currentSortDirection === 'asc' ? 1 : -1;
            }
            return 0;
        });
    }
    
    // 更新排序UI指示器
    function updateSortingUI() {
        document.querySelectorAll('.tasks-table th').forEach(th => {
            th.classList.remove('sorted');
            const icon = th.querySelector('i');
            if (icon) icon.className = 'bi bi-arrow-down-up';
        });
        
        const currentTh = document.querySelector(`.tasks-table th[data-sort="${currentSortField}"]`);
        if (currentTh) {
            currentTh.classList.add('sorted');
            const icon = currentTh.querySelector('i');
            if (icon) {
                icon.className = currentSortDirection === 'asc' ? 
                    'bi bi-arrow-down' : 'bi bi-arrow-up';
            }
        }
    }


    function addComment() {
        const commentInput = document.getElementById('commentInput');
        const comment = commentInput.value.trim();
        
        if (!comment) return;
        
        const selectedRow = document.querySelector('#tasksTableBody tr.selected');
        if (!selectedRow) return;
        
        const taskId = parseInt(selectedRow.dataset.taskId);
        
        fetch(`/api/tasks/${taskId}/comments`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content: comment })
        })
        .then(response => {
            if (response.ok) {
                // 清除输入
                commentInput.value = '';
                
                // 重新加载评论
                loadComments(taskId);
            } else {
                throw new Error('Failed to add comment');
            }
        })
        .catch(error => {
            console.error('Error adding comment:', error);
            alert('Failed to add comment. Please try again later.');
        });
    }

    // ===================================================================
    // ==========================Task Operations==========================
    // ===================================================================
    /**
     * Opens the unified task modal for create/edit
     * @param {number} [taskId] - Task ID for edit mode
     */
    function openTaskModal(taskId) {
        const modal = new bootstrap.Modal(document.getElementById('taskModal'));
        const modalTitle = document.getElementById('taskModalLabel');
        const taskIdInput = document.getElementById('taskId');
        
        // Clear form and reset mode
        document.getElementById('taskForm').reset();
        taskIdInput.value = '';
        
        if (taskId) {
            // Edit mode
            isEditing = true;
            modalTitle.textContent = 'Edit Task';
            taskIdInput.value = taskId;
            
            // Load task data
            fetch(`/api/tasks/${taskId}`)
                .then(response => {
                    if (!response.ok) throw new Error('Failed to load task');
                    return response.json();
                })
                .then(task => {
                    // Populate form fields
                    document.getElementById('title').value = task.title;
                    document.getElementById('description').value = task.description || '';
                    document.getElementById('type').value = task.type;
                    document.getElementById('priority').value = task.priority;
                    document.getElementById('severity').value = task.severity;
                    document.getElementById('status').value = task.status;
                    
                    // Handle assignee dropdown
                    const assigneeSelect = document.getElementById('assignee');
                    if (task.assignee?.id) {
                        assigneeSelect.value = task.assignee.id;
                    } else {
                        assigneeSelect.value = '';
                    }
                    
                    // Handle project dropdown
                    document.getElementById('project').value = task.project?.id || '';
                    
                    // Set dates
                    document.getElementById('start_date').value = formatDateTimeForInput(task.start_date);
                    document.getElementById('due_date').value = formatDateTimeForInput(task.due_date);
                })
                .catch(handleError('Failed to load task details'));
        } else {
            // Create mode
            isEditing = false;
            modalTitle.textContent = 'Create New Task';
        }
        
        modal.show();
    }

    /**
     * Handles task form submission (create/update)
     */
    function handleTaskSubmission() {
        const form = document.getElementById('taskForm');
        const formData = new FormData(form);
        const taskId = formData.get('id');
        
        // Prepare task data
        const taskData = {
            title: formData.get('title'),
            description: formData.get('description'),
            type: formData.get('type'),
            status: formData.get('status'),
            priority: formData.get('priority'),
            severity: formData.get('severity'),
            project_id: parseInt(formData.get('project_id'))
        };
        
        // Optional fields
        const assigneeId = formData.get('assignee_id');
        if (assigneeId) taskData.assignee_id = parseInt(assigneeId);
        
        const startDate = formData.get('start_date');
        if (startDate) taskData.start_date = new Date(startDate).toISOString();
        
        const dueDate = formData.get('due_date');
        if (dueDate) taskData.due_date = new Date(dueDate).toISOString();
        
        // Determine API endpoint and method
        const url = taskId ? `/api/tasks/${taskId}` : '/api/tasks';
        const method = taskId ? 'PUT' : 'POST';
        
        fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(taskData)
        })
        .then(response => {
            if (!response.ok) throw new Error('Task operation failed');
            return response.json();
        })
        .then(() => {
            // Close modal, reload data, and show success
            bootstrap.Modal.getInstance(document.getElementById('taskModal')).hide();
            loadTasks();
            
            // Refresh detail view if editing the current task
            if (taskId && selectedTaskId === parseInt(taskId)) {
                loadTaskDetails(selectedTaskId);
            }
            
            showNotification(isEditing ? 'Task updated successfully!' : 'Task created successfully!');
        })
        .catch(handleError(isEditing ? 'Failed to update task' : 'Failed to create task'));
    }

    /**
     * Handles task row click events
     * @param {Event} e - Click event
     */
    function handleTaskRowClick(e) {
        const row = e.target.closest('tr');
        if (!row || !row.dataset.taskId) return;
        
        const taskId = parseInt(row.dataset.taskId);
        const scrollContainer = document.getElementById('tasksScrollContainer');
        
        // Toggle detail visibility if clicking the same task
        if (selectedTaskId === taskId) {
            detailVisible = !detailVisible;
            if (detailVisible) {
                scrollContainer && (scrollContainer.style.maxHeight = '40vh');
                document.getElementById('taskDetailContainer').style.display = 'block';
                row.classList.add('selected');
            } else {
                scrollContainer && (scrollContainer.style.maxHeight = '70vh');
                document.getElementById('taskDetailContainer').style.display = 'none';
                row.classList.remove('selected');
            }
        } else {
            // Select new task and show details
            selectedTaskId = taskId;
            detailVisible = true;
            
            // Clear previous selections
            document.querySelectorAll('#tasksTableBody tr').forEach(r => {
                r.classList.remove('selected');
            });
            
            // Update UI
            scrollContainer && (scrollContainer.style.maxHeight = '40vh');
            document.getElementById('taskDetailContainer').style.display = 'block';
            row.classList.add('selected');
            
            // Load task details and comments
            loadTaskDetails(taskId);
            loadComments(taskId);
        }
    }

    /**
     * Loads and displays task details
     * @param {number} taskId - Task ID to load
     */
    function loadTaskDetails(taskId) {
        const task = tasks.find(t => t.id === taskId);
        if (!task) return;
        
        const container = document.getElementById('taskDetailContainer');
        container.style.display = 'block';
        
        // Set basic info
        document.getElementById('taskDetailTitle').textContent = task.title || 'Untitled Task';
        document.getElementById('taskDetailDescription').textContent = task.description || 'No description provided';
        
        // Set status and priority badges
        document.getElementById('taskDetailStatus').className = `status-badge ${getStatusClass(task.status)}`;
        document.getElementById('taskDetailStatus').textContent = getStatusText(task.status);
        document.getElementById('taskDetailPriority').className = `badge ${getPriorityClass(task.priority)}`;
        document.getElementById('taskDetailPriority').textContent = getPriorityText(task.priority);
        
        // Set additional details
        document.getElementById('taskDetailType').textContent = task.type ? task.type.charAt(0).toUpperCase() + task.type.slice(1) : 'Unknown';
        document.getElementById('taskDetailSeverity').textContent = task.severity ? task.severity.charAt(0).toUpperCase() + task.severity.slice(1) : 'Unknown';
        document.getElementById('taskDetailCreated').textContent = formatDate(task.created_at);
        document.getElementById('taskDetailUpdated').textContent = formatDate(task.updated_at);
        
        // Set project info
        const projectName = task.project?.name || 'No Project';
        const categoryName = task.project?.category?.name || 'No Category';
        const categoryType = task.project?.category?.type || '';
        document.getElementById('taskDetailProject').textContent = projectName;
        document.getElementById('taskDetailCategory').textContent = `${categoryName}${categoryType ? ` (${categoryType})` : ''}`;
        
        // Set assignee info
        const assigneeName = task.assignee?.full_name || task.assignee?.username || 'Unassigned';
        document.getElementById('taskDetailAssignee').textContent = assigneeName;
        
        // Set dates
        document.getElementById('taskDetailStartDate').textContent = formatDate(task.start_date);
        document.getElementById('taskDetailDueDate').textContent = formatDate(task.due_date);
    }

    /**
     * Closes the task detail panel
     */
    function closeTaskDetail() {
        const scrollContainer = document.getElementById('tasksScrollContainer');
        const detailContainer = document.getElementById('taskDetailContainer');
        
        // Reset UI
        scrollContainer && (scrollContainer.style.maxHeight = '70vh');
        detailContainer && (detailContainer.style.display = 'none');
        
        // Clear selection
        if (selectedTaskId) {
            const selectedRow = document.querySelector(`#tasksTableBody tr[data-task-id="${selectedTaskId}"]`);
            selectedRow && selectedRow.classList.remove('selected');
        }
        
        // Reset state
        detailVisible = false;
        selectedTaskId = null;
    }
    function openEditTaskModal() {
        const taskId = selectedTaskId;
        console.info("taskID: ", taskId)
        fetch(`/api/tasks/${taskId}`)
            .then(response => response.json())
            .then(task => {
                // 设置表单值
                document.getElementById('editTaskId').value      = task.id;
                document.getElementById('editTitle').value       = task.title;
                document.getElementById('editDescription').value = task.description || '';
                document.getElementById('editType').value        = task.type;
                document.getElementById('editPriority').value    = task.priority;
                document.getElementById('editSeverity').value    = task.severity;
                document.getElementById('editStatus').value      = task.status;
                document.getElementById('editAssignee').value    = task.assignee.id;
                document.getElementById('editProject').value     = task.project.id;
                
                // 修改后的日期时间格式化函数（北京时间）
                const formatDateForInput = (dateString) => {
                    if (!dateString) return '';
                    
                    // 转换为北京时间（UTC+8）
                    const date = new Date(dateString);
                    const beijingTime = date.getTime() + 8 * 60 * 60 * 1000;
                    const beijingDate = new Date(beijingTime);
                    
                    // 格式化组件
                    const year = beijingDate.getUTCFullYear();
                    const month = String(beijingDate.getUTCMonth() + 1).padStart(2, '0');
                    const day = String(beijingDate.getUTCDate()).padStart(2, '0');
                    const hours = String(beijingDate.getUTCHours()).padStart(2, '0');
                    const minutes = String(beijingDate.getUTCMinutes()).padStart(2, '0');
                    
                    return `${year}-${month}-${day}T${hours}:${minutes}`;
                };
                
                document.getElementById('editStartDate').value = formatDateForInput(task.start_date);
                document.getElementById('editDueDate').value = formatDateForInput(task.due_date);
                
                // 显示模态框
                const modal = new bootstrap.Modal(document.getElementById('editTaskModal'));
                modal.show();
            })
            .catch(error => {
                console.error('Error loading task for editing:', error);
                alert('Failed to load task details for editing. Please try again later.');
            });
    }

    function saveTaskChanges() {
        const taskId = document.getElementById('editTaskId').value;
        const taskData = {
            title: document.getElementById('editTitle').value,
            description: document.getElementById('editDescription').value,
            type: document.getElementById('editType').value,
            priority: document.getElementById('editPriority').value,
            severity: document.getElementById('editSeverity').value,
            status: document.getElementById('editStatus').value,
            assignee_id: document.getElementById('editAssignee').value,
            project_id: document.getElementById('editProject').value,
            start_date: document.getElementById('editStartDate').value,
            due_date: document.getElementById('editDueDate').value
        };
        
        fetch(`/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(taskData)
        })
        .then(response => {
            if (response.ok) {
                // 关闭模态框
                const modal = bootstrap.Modal.getInstance(document.getElementById('editTaskModal'));
                modal.hide();
                
                // 重新加载任务
                loadTasks();
                
                // 如果显示了任务详情，更新它
                const selectedRow = document.querySelector('#tasksTableBody tr.selected');
                if (selectedRow) {
                    loadTaskDetails(parseInt(taskId));
                }
                
                alert('Task updated successfully!');
            } else {
                throw new Error('Failed to update task');
            }
        })
        .catch(error => {
            console.error('Error updating task:', error);
            alert('Failed to update task. Please try again later.');
        });
    }

    // region Create Task
    function createTask() {
        const form = document.getElementById('createTaskForm');
        const formData = new FormData(form);
        
        const taskData = {
            title      : formData.get('title'),
            description: formData.get('description'),
            type       : formData.get('type'),
            status     : formData.get('status'),
            priority   : formData.get('priority'),
            severity   : formData.get('severity'),
            project_id : parseInt(formData.get('project_id'))
        };
        
        const assigneeId = formData.get('assignee_id');
        if (assigneeId) {
            taskData.assignee_id = parseInt(assigneeId);
        }
        
        const startDate = formData.get('start_date');
        if (startDate) {
            taskData.start_date = new Date(startDate).toISOString();
        }
        
        const dueDate = formData.get('due_date');
        if (dueDate) {
            taskData.due_date = new Date(dueDate).toISOString();
        }
        
        fetch('/api/tasks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(taskData)
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Failed to create task');
        })
        .then(data => {
            // 关闭模态框并重置表单
            const modal = bootstrap.Modal.getInstance(document.getElementById('createTaskModal'));
            modal.hide();
            form.reset();
            
            // 重新加载任务
            loadTasks();
            
            alert('Task created successfully!');
        })
        .catch(error => {
            console.error('Error creating task:', error);
            alert('Failed to create task. Please try again later.');
        });
    }
}
// 确保在全局可用
window.initTaskManagement = initTaskManagement;
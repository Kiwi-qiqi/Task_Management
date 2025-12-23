/**
 * Task Management System
 * Handles task CRUD operations, filtering, sorting, and comments
 */
function initTaskManagement() {
    // console.info('[INIT] Task Management System initializing');

    // ==================================================================
    // Application State
    // ==================================================================
    let tasks = [];
    let currentSortField = 'title';
    let currentSortDirection = 'asc';
    let selectedTaskId = null;
    let detailVisible = false;
    let isEditing = false;

    // ==================================================================
    // Utility Functions
    // ==================================================================
    
    /**
     * Format date string to Beijing timezone (UTC+8)
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date string (YYYY-MM-DD)
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
            // console.error('[FORMAT_DATE] Invalid date:', dateString, e);
            return 'Invalid date';
        }
    }

    /**
     * Format date for datetime-local input field
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date string for input
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
            return `${year}-${month}-${day}`;
        } catch (e) {
            // console.warn('[FORMAT_DATETIME] Invalid date format:', dateString, e);
            return '';
        }
    }

    /**
     * Debounce function to limit event handler calls
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} Debounced function
     */
    function debounce(func, wait) {
        let timeout;
        return function() {
            const context = this;
            const args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), wait);
        };
    }

    /**
     * Populate dropdown with options
     * @param {string} elementId - Dropdown element ID
     * @param {Array} items - Array of items to populate
     * @param {string} primaryField - Primary field for display text
     * @param {string} fallbackField - Fallback field for display text
     * @param {string} userRole - Current user role
     */
    function populateDropdown(elementId, items, primaryField, fallbackField = null, userRole = 'employee') {
        const dropdown = document.getElementById(elementId);
        if (!dropdown) {
            // console.error('[POPULATE_DROPDOWN] Element not found:', elementId);
            return;
        }
        
        dropdown.innerHTML = '';
        
        // Add "All" option for filters
        if (elementId === 'assigneeFilter') {
            if (userRole === 'System Administrator' || userRole === 'Admin') {
                const allOption = document.createElement('option');
                allOption.value = 'all';
                allOption.textContent = 'All Assignees';
                dropdown.appendChild(allOption);
            }
        } else if (elementId === 'projectFilter') {
            const allOption = document.createElement('option');
            allOption.value = 'all';
            allOption.textContent = 'All Projects';
            dropdown.appendChild(allOption);
        }
        
        // Populate with data items
        items.forEach(item => {
            const option = document.createElement('option');
            
            // Set correct value based on dropdown type
            if (elementId === 'projectFilter' || elementId === 'project') {
                option.value = item.id; // Use database ID for projects
            } else if (elementId === 'assigneeFilter') {
                option.value = item.userID; // Use userID for assignee filter
            } else if (elementId === 'assignee') {
                option.value = item.id; // Use database ID for assignee assignment
            }
            
            option.textContent = item[primaryField] || (fallbackField && item[fallbackField]) || `Item ${item.id}`;
            dropdown.appendChild(option);
        });
        
        // console.log('[POPULATE_DROPDOWN] Populated', elementId, 'with', items.length, 'items');
    }

    /**
     * Get CSS class for priority
     * @param {string} priority - Priority value
     * @returns {string} CSS class name
     */
    function getPriorityClass(priority) {
        const p = (priority || '').toLowerCase();
        const classes = {
            high: 'priority-high',
            medium: 'priority-medium',
            low: 'priority-low',
            urgent: 'priority-urgent'
        };
        return classes[p] || 'priority-unknown';
    }

    /**
     * Get display text for priority
     * @param {string} priority - Priority value
     * @returns {string} Display text
     */
    function getPriorityText(priority) {
        const p = (priority || '').toLowerCase();
        const texts = {
            high: 'High',
            medium: 'Medium',
            low: 'Low',
            urgent: 'Urgent'
        };
        return texts[p] || 'Unknown';
    }

    /**
     * Get CSS class for status
     * @param {string} status - Status value
     * @returns {string} CSS class name
     */
    function getStatusClass(status) {
        const s = (status || '').toLowerCase();
        const classes = {
            todo: 'status-todo',
            in_progress: 'status-in_progress',
            review: 'status-review',
            done: 'status-done'
        };
        return classes[s] || 'status-unknown';
    }

    /**
     * Get display text for status
     * @param {string} status - Status value
     * @returns {string} Display text
     */
    function getStatusText(status) {
        const s = (status || '').toLowerCase();
        const texts = {
            todo: 'To Do',
            in_progress: 'In Progress',
            review: 'In Review',
            done: 'Done'
        };
        return texts[s] || 'Unknown';
    }

    /**
     * Show error notification to user
     * @param {string} message - Error message
     */
    function showErrorNotification(message) {
        // console.error('[ERROR]', message);
        alert(message);
    }

    /**
     * Generic error handler
     * @param {string} message - Error message
     * @returns {Function} Error handler function
     */
    function handleError(message) {
        return function(error) {
            // console.error('[ERROR]', message, error);
            try {
                showErrorNotification(message);
            } catch (e) {
                alert(message);
            }
        };
    }

    /**
     * Show success notification to user
     * @param {string} message - Success message
     */
    function showNotification(message) {
        // console.log('[NOTIFICATION]', message);
        try {
            alert(message);
        } catch (e) {
            // console.log('[NOTIFICATION]', message);
        }
    }

    // ==================================================================
    // Data Loading Functions
    // ==================================================================
    
    /**
     * Load users based on current user role and permissions
     */
    function loadUsers() {
        // Get current user information from hidden inputs
        const currentId = document.getElementById('currentId')?.value;
        const currentUserId = document.getElementById('currentUserId')?.value;
        const currentUserName = document.getElementById('currentUserName')?.value;
        const currentFullName = document.getElementById('currentFullName')?.value;
        const currentUserTitle = document.getElementById('currentUserTitle')?.value;
        
        // console.log('[LOAD_USERS] Loading users for role:', currentUserTitle);
        
        // Fetch admin-employee mapping from backend
        fetch('/api/admin-employee-map')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load admin map: ' + response.status);
                }
                return response.json();
            })
            .then(adminEmployeeMap => {
                // console.log('[LOAD_USERS] Admin-employee map loaded');
                loadUsersByRole(currentUserId, currentUserTitle, adminEmployeeMap);
            })
            .catch(error => {
                // console.error('[LOAD_USERS] Error loading admin map:', error);
                showErrorNotification('Failed to load permission mapping. Please try again later.');
            });
        
        /**
         * Load users filtered by role
         * @param {string} userId - Current user ID
         * @param {string} userTitle - Current user title/role
         * @param {Object} adminEmployeeMap - Admin-employee mapping
         */
        function loadUsersByRole(userId, userTitle, adminEmployeeMap) {
            if (userTitle === 'System Administrator') {
                // System admin: Load all users
                fetch('/api/users')
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('Failed to load users: ' + response.status);
                        }
                        return response.json();
                    })
                    .then(users => {
                        // console.log('[LOAD_USERS] System Admin - Loaded', users.length, 'users');
                        populateDropdown('assigneeFilter', users, 'full_name', 'username', 'System Administrator');
                        populateDropdown('assignee', users, 'full_name', 'username', 'System Administrator');
                    })
                    .catch(error => {
                        // console.error('[LOAD_USERS] Error loading users:', error);
                        showErrorNotification('Failed to load users. Please try again later.');
                    });
            } else if (adminEmployeeMap[userId]) {
                // Secondary admin: Load self and managed employees
                fetch('/api/users')
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('Failed to load users: ' + response.status);
                        }
                        return response.json();
                    })
                    .then(users => {
                        const managedEmployeeIds = adminEmployeeMap[userId];
                        const filteredUsers = users.filter(user => 
                            user.userID === userId || managedEmployeeIds.includes(user.userID)
                        );
                        
                        // console.log('[LOAD_USERS] Admin - Loaded', filteredUsers.length, 'filtered users');
                        populateDropdown('assigneeFilter', filteredUsers, 'full_name', 'username', 'Admin');
                        populateDropdown('assignee', filteredUsers, 'full_name', 'username', 'Admin');
                    })
                    .catch(error => {
                        // console.error('[LOAD_USERS] Error loading users:', error);
                        showErrorNotification('Failed to load users. Please try again later.');
                    });
            } else {
                // Regular employee: Only show current user
                const currentUser = [{
                    id: currentId,
                    userID: currentUserId,
                    username: currentUserName,
                    full_name: currentFullName,
                    title: currentUserTitle
                }];
                
                // console.log('[LOAD_USERS] Employee - Loaded current user only');
                populateDropdown('assigneeFilter', currentUser, 'full_name', 'username', 'Employee');
                populateDropdown('assignee', currentUser, 'full_name', 'username', 'Employee');
            }
        }
    }

    /**
     * Load all projects from backend
     */
    function loadProjects() {
        // console.log('[LOAD_PROJECTS] Loading projects');
        fetch('/api/projects')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load projects: ' + response.status);
                }
                return response.json();
            })
            .then(projects => {
                // console.log('[LOAD_PROJECTS] Loaded', projects.length, 'projects');
                populateDropdown('projectFilter', projects, 'name');
                populateDropdown('project', projects, 'name');
            })
            .catch(error => {
                // console.error('[LOAD_PROJECTS] Error:', error);
                showErrorNotification('Failed to load projects. Please try again later.');
            });
    }

    /**
     * Load tasks with current filter parameters
     */
    function loadTasks() {
        const params = new URLSearchParams();
        
        // Get filter values
        const status = document.getElementById('statusFilter')?.value;
        const assignee = document.getElementById('assigneeFilter')?.value;
        const project = document.getElementById('projectFilter')?.value;
        const priority = document.getElementById('priorityFilter')?.value;
        const text = document.getElementById('textSearch')?.value;

        // Build query parameters
        if (status && status !== 'all') params.append('status', status);
        if (assignee && assignee !== 'all') params.append('assignee', assignee);
        if (project && project !== 'all') params.append('project', project);
        if (priority && priority !== 'all') params.append('priority', priority);
        if (text) params.append('search_text', text);

        // console.log('[LOAD_TASKS] Loading tasks with params:', params.toString());
        
        fetch('/api/tasks?' + params.toString())
            .then(response => response.json())
            .then(data => {
                tasks = data;
                sortTasks();
                renderTasksTable(tasks);
                // console.log('[LOAD_TASKS] Loaded', tasks.length, 'tasks');
            })
            .catch(error => {
                // console.error('[LOAD_TASKS] Error:', error);
                showErrorNotification('Failed to load tasks');
            });
    }

    /**
     * Load comments for a specific task
     * @param {number} taskId - Task ID
     */
    function loadComments(taskId) {
        // console.log('[LOAD_COMMENTS] Loading comments for task:', taskId);
        fetch('/api/tasks/' + taskId + '/comments', { credentials: 'same-origin' })
            .then(response => {
                if (!response.ok) {
                    const contentType = response.headers.get('content-type') || '';
                    if (contentType.includes('application/json')) {
                        return response.json().then(json => {
                            throw new Error(json.error || 'Failed to load comments: ' + response.status);
                        });
                    }
                    return response.text().then(text => {
                        throw new Error(text || 'Failed to load comments: ' + response.status);
                    });
                }
                const contentType = response.headers.get('content-type') || '';
                if (!contentType.includes('application/json')) {
                    return response.text().then(() => {
                        throw new Error('Server returned non-JSON response');
                    });
                }
                return response.json();
            })
            .then(comments => {
                // console.log('[LOAD_COMMENTS] Loaded', comments.length, 'comments');
                renderComments(comments);
            })
            .catch(error => {
                // console.error('[LOAD_COMMENTS] Error:', error);
                const message = (error.message && error.message.includes('Authentication')) 
                    ? 'Authentication required. Please login.' 
                    : 'Failed to load comments. Please try again later.';
                alert(message);
            });
    }

    // ==================================================================
    // Rendering Functions
    // ==================================================================
    
    /**
     * Render tasks table with current task data
     * @param {Array} tasks - Array of task objects
     */
    function renderTasksTable(tasks) {
        const tableBody = document.getElementById('tasksTableBody');
        const tasksCount = document.getElementById('tasksCount');
        
        if (!tableBody || !tasksCount) {
            // console.error('[RENDER_TASKS] Table elements not found');
            return;
        }
        
        tableBody.innerHTML = '';
        tasksCount.textContent = tasks.length;
        
        // Show empty state if no tasks
        if (tasks.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-5">
                        <div class="empty-state">
                            <i class="bi bi-inbox"></i>
                            <h4>No tasks found</h4>
                            <p>Try adjusting your search criteria</p>
                        </div>
                    </td>
                </tr>`;
            return;
        }
        
        // Render each task row
        tasks.forEach(task => {
            const row = document.createElement('tr');
            row.dataset.taskId = task.id;
            
            if (selectedTaskId === task.id && detailVisible) {
                row.classList.add('selected');
            }
            
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
                <td class="actions-column">
                    <button class="btn action-btn btn-outline-primary edit-task-btn" data-task-id="${task.id}">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn action-btn btn-outline-danger delete-task-btn" data-task-id="${task.id}">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            `;
            
            tableBody.appendChild(row);
        });
        
        // console.log('[RENDER_TASKS] Rendered', tasks.length, 'task rows');
    }

    /**
     * Render comments for current task
     * @param {Array} comments - Array of comment objects
     */
    function renderComments(comments) {
        const container = document.getElementById('commentsContainer');
        if (!container) {
            // console.error('[RENDER_COMMENTS] Container not found');
            return;
        }
        
        container.innerHTML = '';
        
        if (!comments || comments.length === 0) {
            container.innerHTML = '<p class="text-muted">No comments yet</p>';
            return;
        }
        
        comments.forEach(comment => {
            const commentCard = document.createElement('div');
            commentCard.className = 'comment-card';
            
            // Format comment date
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
                // console.warn('[RENDER_COMMENTS] Invalid date format:', comment.created_at);
            }
            
            // Create comment header with delete button
            commentCard.innerHTML = `
                <div class="comment-header">
                    <div class="comment-date">${formattedDate}</div>
                    <button class="action-btn delete-btn" data-id="${comment.id}" title="Delete">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            `;

            // Create content div with proper line break handling
            const contentDiv = document.createElement('div');
            contentDiv.className = 'comment-content';
            contentDiv.style.whiteSpace = 'pre-wrap';
            contentDiv.textContent = comment.content || 'No content';
            commentCard.appendChild(contentDiv);

            // Render attachments if present
            if (Array.isArray(comment.attachments) && comment.attachments.length > 0) {
                const attList = document.createElement('ul');
                attList.className = 'comment-attachments list-unstyled mt-2';
                comment.attachments.forEach(att => {
                    const li = document.createElement('li');
                    const a = document.createElement('a');
                    a.href = att.download_url || '/api/attachments/' + att.id;
                    a.textContent = att.filename || 'Attachment ' + att.id;
                    a.target = '_blank';
                    li.appendChild(a);
                    attList.appendChild(li);
                });
                commentCard.appendChild(attList);
            }
            
            container.appendChild(commentCard);
        });
        
        // console.log('[RENDER_COMMENTS] Rendered', comments.length, 'comments');
    }

    /**
     * Load and display task details
     * @param {number} taskId - Task ID
     */
    function loadTaskDetails(taskId) {
        // console.log('[LOAD_TASK_DETAILS] Loading details for task:', taskId);
        fetch('/api/tasks/' + taskId)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load task details');
                }
                return response.json();
            })
            .then(task => {
                // Update task in global tasks array
                const index = tasks.findIndex(t => t.id === taskId);
                if (index !== -1) {
                    tasks[index] = task;
                }
                
                renderTaskDetails(task);
                // console.log('[LOAD_TASK_DETAILS] Task details loaded');
            })
            .catch(error => {
                // console.error('[LOAD_TASK_DETAILS] Error:', error);
                showNotification('Failed to load task details', 'error');
            });
    }

    /**
     * Render task details in detail panel
     * @param {Object} task - Task object
     */
    function renderTaskDetails(task) {
        const container = document.getElementById('taskDetailContainer');
        if (!container) {
            // console.error('[RENDER_TASK_DETAILS] Container not found');
            return;
        }
        
        container.style.display = 'block';
        
        // Basic task info
        document.getElementById('taskDetailTitle').textContent = task.title || 'Untitled Task';
        document.getElementById('taskDetailDescription').textContent = task.description || 'No description';
        
        // Status and priority badges
        const statusBadge = document.getElementById('taskDetailStatus');
        statusBadge.className = 'badge ' + getStatusClass(task.status);
        statusBadge.textContent = getStatusText(task.status);
        
        const priorityBadge = document.getElementById('taskDetailPriority');
        priorityBadge.className = 'badge ' + getPriorityClass(task.priority);
        priorityBadge.textContent = getPriorityText(task.priority);
        
        // Type and severity
        document.getElementById('taskDetailType').textContent = task.type 
            ? task.type.charAt(0).toUpperCase() + task.type.slice(1) 
            : 'Unknown';
        document.getElementById('taskDetailSeverity').textContent = task.severity 
            ? task.severity.charAt(0).toUpperCase() + task.severity.slice(1) 
            : 'Unknown';
        
        // Dates
        document.getElementById('taskDetailCreated').textContent = formatDate(task.created_at);
        document.getElementById('taskDetailUpdated').textContent = formatDate(task.updated_at);
        document.getElementById('taskDetailStartDate').textContent = formatDate(task.start_date);
        document.getElementById('taskDetailDueDate').textContent = formatDate(task.due_date);
        
        // Project info
        const projectName = task.project?.name || 'No Project';
        document.getElementById('taskDetailProject').textContent = projectName;
        
        // Assignee info
        const assigneeName = task.assignee?.full_name || task.assignee?.username || 'Unassigned';
        document.getElementById('taskDetailAssignee').textContent = assigneeName;
        
        // Setup edit button
        const editBtn = document.getElementById('editTaskBtn');
        if (editBtn) {
            editBtn.onclick = () => openTaskModal(task.id);
        }
        
        // console.log('[RENDER_TASK_DETAILS] Task details rendered');
    }

    // ==================================================================
    // Event Handlers & UI Actions
    // ==================================================================
    
    /**
     * Reset all filters to default values
     */
    function resetFilters() {
        // console.log('[RESET_FILTERS] Resetting all filters');
        
        document.getElementById('statusFilter').value = 'all';
        document.getElementById('projectFilter').value = 'all';
        document.getElementById('priorityFilter').value = 'all';
        document.getElementById('textSearch').value = '';
        document.getElementById('assigneeFilter').value = 'all';
        
        loadTasks();
    }

    /**
     * Close task detail panel
     */
    function closeTaskDetail() {
        // console.log('[CLOSE_DETAIL] Closing task detail panel');
        
        const scrollContainer = document.getElementById('tasksScrollContainer');
        const detailContainer = document.getElementById('taskDetailContainer');
        
        if (scrollContainer) scrollContainer.style.maxHeight = '70vh';
        if (detailContainer) detailContainer.style.display = 'none';
        
        if (selectedTaskId) {
            const selectedRow = document.querySelector('#tasksTableBody tr[data-task-id="' + selectedTaskId + '"]');
            if (selectedRow) selectedRow.classList.remove('selected');
        }
        
        detailVisible = false;
        selectedTaskId = null;
    }

    /**
     * Handle task row click event
     * @param {Event} e - Click event
     */
    function handleTaskRowClick(e) {
        // Ignore clicks on action buttons
        const editBtn = e.target.closest('.edit-task-btn');
        const deleteBtn = e.target.closest('.delete-task-btn');
        
        if (editBtn || deleteBtn) {
            return;
        }
        
        const row = e.target.closest('tr');
        if (!row || !row.dataset.taskId) return;
        
        const taskId = parseInt(row.dataset.taskId);
        const scrollContainer = document.getElementById('tasksScrollContainer');
        const detailContainer = document.getElementById('taskDetailContainer');
        
        // console.log('[TASK_ROW_CLICK] Task ID:', taskId);
        
        // Toggle detail panel if same task clicked
        if (selectedTaskId === taskId) {
            detailVisible = !detailVisible;
            if (detailVisible) {
                if (scrollContainer) scrollContainer.style.maxHeight = '40vh';
                detailContainer.style.display = 'block';
                row.classList.add('selected');
                loadTaskDetails(taskId);
                loadComments(taskId);
            } else {
                if (scrollContainer) scrollContainer.style.maxHeight = '70vh';
                detailContainer.style.display = 'none';
                row.classList.remove('selected');
            }
        } else {
            // Show detail for new task
            selectedTaskId = taskId;
            detailVisible = true;
            
            document.querySelectorAll('#tasksTableBody tr').forEach(r => r.classList.remove('selected'));
            if (scrollContainer) scrollContainer.style.maxHeight = '40vh';
            detailContainer.style.display = 'block';
            row.classList.add('selected');
            
            loadTaskDetails(taskId);
            loadComments(taskId);
        }
    }

    /**
     * Setup all event listeners
     */
    function setupEventListeners() {
        // console.log('[SETUP_LISTENERS] Setting up event listeners');
        
        // Table row click
        const tableBody = document.getElementById('tasksTableBody');
        if (tableBody) {
            tableBody.addEventListener('click', handleTaskRowClick);
        }
        
        // Filter change events
        ['statusFilter', 'assigneeFilter', 'projectFilter', 'priorityFilter'].forEach(id => {
            const filter = document.getElementById(id);
            if (filter) filter.addEventListener('change', loadTasks);
        });
        
        // Text search with debounce
        const textSearch = document.getElementById('textSearch');
        if (textSearch) {
            textSearch.addEventListener('input', debounce(loadTasks, 300));
        }
        
        // Button click events
        const resetBtn = document.getElementById('resetFilters');
        if (resetBtn) resetBtn.addEventListener('click', resetFilters);
        
        const createBtn = document.getElementById('createTaskBtn');
        if (createBtn) createBtn.addEventListener('click', () => openTaskModal());
        
        const editBtn = document.getElementById('editTaskBtn');
        if (editBtn) editBtn.addEventListener('click', () => openTaskModal(selectedTaskId));
        
        const submitBtn = document.getElementById('submitTaskForm');
        if (submitBtn) submitBtn.addEventListener('click', handleTaskSubmission);
        
        const cancelBtn = document.getElementById('cancelbtn');
        if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
        
        const closeDetail = document.getElementById('closeDetailBtn');
        if (closeDetail) closeDetail.addEventListener('click', closeTaskDetail);
        
        // Comment form submission
        const addCommentForm = document.getElementById('addCommentForm');
        if (addCommentForm) {
            addCommentForm.addEventListener('submit', function(e) {
                e.preventDefault();
                addComment();
            });
        }
        
        // Comment delete button
        const commentsContainer = document.getElementById('commentsContainer');
        if (commentsContainer) {
            commentsContainer.addEventListener('click', function(e) {
                if (e.target.closest('.delete-btn')) {
                    const btn = e.target.closest('.delete-btn');
                    const commentId = btn.dataset.id;
                    if (commentId) {
                        deleteComment(commentId);
                    }
                }
            });
        }
        
        // Task action buttons (edit/delete)
        if (tableBody) {
            tableBody.addEventListener('click', function(e) {
                if (e.target.closest('.edit-task-btn')) {
                    const btn = e.target.closest('.edit-task-btn');
                                        const taskId = btn.dataset.taskId;
                    if (taskId) {
                        openTaskModal(taskId);
                    }
                }
                else if (e.target.closest('.delete-task-btn')) {
                    const btn = e.target.closest('.delete-task-btn');
                    const taskId = btn.dataset.taskId;
                    if (taskId) {
                        deleteTask(taskId);
                    }
                }
            });
        }
    }

    /**
     * Delete a task
     * @param {number} taskId - Task ID to delete
     */
    function deleteTask(taskId) {
        if (!confirm('Are you sure you want to delete this task? This action cannot be undone.')) {
            return;
        }

        // console.log('[DELETE_TASK] Deleting task:', taskId);
        
        fetch('/api/tasks/' + taskId, {
            method: 'DELETE',
            credentials: 'same-origin'
        })
        .then(response => {
            if (response.ok) {
                // Remove task row from table
                const row = document.querySelector('#tasksTableBody tr[data-task-id="' + taskId + '"]');
                if (row) row.remove();
                
                // Clear detail panel if deleted task was selected
                if (selectedTaskId == taskId) {
                    selectedTaskId = null;
                    detailVisible = false;
                    closeTaskDetail();
                }
                
                // console.log('[DELETE_TASK] Task deleted successfully');
                showNotification('Task deleted successfully', 'success');
            } else {
                return response.json().then(data => {
                    throw new Error(data.error || 'Failed to delete task');
                });
            }
        })
        .catch(error => {
            // console.error('[DELETE_TASK] Error:', error);
            showNotification(error.message || 'Failed to delete task. Please try again later.', 'error');
        });
    }

    // ==================================================================
    // Comment Functions
    // ==================================================================
    
    /**
     * Add a new comment to current task
     */
    function addComment() {
        const commentInput = document.getElementById('commentInput');
        const comment = commentInput ? commentInput.value.trim() : '';
        
        if (!comment) {
            // console.warn('[ADD_COMMENT] Empty comment');
            return;
        }

        const selectedRow = document.querySelector('#tasksTableBody tr.selected');
        if (!selectedRow) {
            // console.error('[ADD_COMMENT] No task selected');
            return;
        }
        
        const taskId = parseInt(selectedRow.dataset.taskId);
        // console.log('[ADD_COMMENT] Adding comment to task:', taskId);

        const filesInput = document.getElementById('commentFiles');
        const formData = new FormData();
        formData.append('content', comment);
        
        // Add file attachments if present
        if (filesInput && filesInput.files && filesInput.files.length > 0) {
            for (let i = 0; i < filesInput.files.length; i++) {
                formData.append('files', filesInput.files[i]);
            }
        }

        fetch('/api/tasks/' + taskId + '/comments', {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        })
        .then(response => {
            if (response.ok) {
                commentInput.value = '';
                if (filesInput) filesInput.value = '';
                loadComments(taskId);
                // console.log('[ADD_COMMENT] Comment added successfully');
            } else {
                const contentType = response.headers.get('content-type') || '';
                if (contentType.includes('application/json')) {
                    return response.json().then(json => {
                        throw new Error(json.error || 'Failed to add comment');
                    });
                }
                return response.text().then(text => {
                    throw new Error(text || 'Failed to add comment');
                });
            }
        })
        .catch(error => {
            // console.error('[ADD_COMMENT] Error:', error);
            alert('Failed to add comment. Please try again later.');
        });
    }

    /**
     * Delete a comment
     * @param {number} commentId - Comment ID to delete
     */
    function deleteComment(commentId) {
        if (!confirm('Are you sure you want to delete this comment? This action cannot be undone.')) {
            return;
        }
        
        // console.log('[DELETE_COMMENT] Deleting comment:', commentId);
        
        fetch('/api/comments/' + commentId, {
            method: 'DELETE',
            credentials: 'same-origin'
        })
        .then(response => {
            if (response.ok) {
                // Reload comments for current task
                const selectedRow = document.querySelector('#tasksTableBody tr.selected');
                if (selectedRow) {
                    const taskId = parseInt(selectedRow.dataset.taskId);
                    loadComments(taskId);
                }
                // console.log('[DELETE_COMMENT] Comment deleted successfully');
            } else {
                const contentType = response.headers.get('content-type') || '';
                if (contentType.includes('application/json')) {
                    return response.json().then(json => {
                        throw new Error(json.error || 'Failed to delete comment');
                    });
                }
                return response.text().then(text => {
                    throw new Error(text || 'Failed to delete comment');
                });
            }
        })
        .catch(error => {
            // console.error('[DELETE_COMMENT] Error:', error);
            alert('Failed to delete comment. Please try again later.');
        });
    }

    // ==================================================================
    // Modal & CRUD Operations
    // ==================================================================
    
    /**
     * Open task modal for create or edit
     * @param {number} taskId - Task ID for edit mode, null for create mode
     */
    function openTaskModal(taskId) {
        const modalEl = document.getElementById('taskModal');
        const modal = new bootstrap.Modal(modalEl);
        const modalTitle = document.getElementById('taskModalLabel');
        const taskIdInput = document.getElementById('taskId');
        
        // Reset form
        document.getElementById('taskForm').reset();
        taskIdInput.value = '';
        
        if (taskId) {
            // Edit mode
            isEditing = true;
            modalTitle.textContent = 'Edit Task';
            taskIdInput.value = taskId;
            
            // console.log('[OPEN_MODAL] Edit mode for task:', taskId);
            
            fetch('/api/tasks/' + taskId)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Failed to load task');
                    }
                    return response.json();
                })
                .then(task => {
                    // Populate form fields
                    document.getElementById('title').value = task.title || '';
                    document.getElementById('description').value = task.description || '';
                    document.getElementById('type').value = task.type || 'task';
                    document.getElementById('priority').value = task.priority || 'medium';
                    document.getElementById('severity').value = task.severity || 'normal';
                    document.getElementById('status').value = task.status || 'todo';
                    
                    // Set assignee dropdown
                    const assigneeSelect = document.getElementById('assignee');
                    if (assigneeSelect && task.assignee?.id) {
                        assigneeSelect.value = task.assignee.id;
                    }
                    
                    // Set project dropdown
                    const projectSelect = document.getElementById('project');
                    if (projectSelect && task.project?.id) {
                        projectSelect.value = task.project.id;
                    }
                    
                    // Set dates
                    document.getElementById('start_date').value = formatDate(task.start_date);
                    document.getElementById('due_date').value = formatDate(task.due_date);
                    
                    // console.log('[OPEN_MODAL] Task data loaded');
                })
                .catch(handleError('Failed to load task details'));
        } else {
            // Create mode
            isEditing = false;
            modalTitle.textContent = 'Create New Task';
            
            // Set default start date to today
            const today = new Date();
            const formattedDate = formatDate(today.toISOString());
            document.getElementById('start_date').value = formattedDate;
            
            // console.log('[OPEN_MODAL] Create mode');
        }
        
        modal.show();
    }

    /**
     * Handle task form submission (create or update)
     */
    function handleTaskSubmission() {
        const form = document.getElementById('taskForm');
        const formData = new FormData(form);
        const taskId = formData.get('id');
        const isEditing = !!taskId;
        
        // console.log('[SUBMIT_TASK] Submitting task, edit mode:', isEditing);
        
        // Prepare task data object
        const taskData = {
            title: formData.get('title'),
            description: formData.get('description'),
            type: formData.get('type'),
            status: formData.get('status'),
            priority: formData.get('priority'),
            severity: formData.get('severity')
        };
        
        // Validate and set project_id
        const projectValue = formData.get('project_id');
        // console.log('[SUBMIT_TASK] Project value:', projectValue);
        
        if (projectValue && projectValue !== '' && projectValue !== 'null' && projectValue !== 'undefined') {
            taskData.project_id = parseInt(projectValue);
            // console.log('[SUBMIT_TASK] Valid project_id:', taskData.project_id);
        } else {
            // console.error('[SUBMIT_TASK] Invalid project_id:', projectValue);
            showNotification('Please select a project', 'error');
            return;
        }
        
        // Set assignee_id if provided
        const assigneeValue = formData.get('assignee_id');
        if (assigneeValue && assigneeValue !== '' && assigneeValue !== 'null' && assigneeValue !== 'undefined') {
            taskData.assignee_id = parseInt(assigneeValue);
            // console.log('[SUBMIT_TASK] Valid assignee_id:', taskData.assignee_id);
        }
        
        // Handle date fields
        const startDate = formData.get('start_date');
        if (startDate) {
            taskData.start_date = new Date(startDate).toISOString();
        }
        
        const dueDate = formData.get('due_date');
        if (dueDate) {
            taskData.due_date = new Date(dueDate).toISOString();
        }
        
        // console.log('[SUBMIT_TASK] Final task data:', JSON.stringify(taskData, null, 2));
        
        // Determine API endpoint and method
        const url = taskId ? '/api/tasks/' + taskId : '/api/tasks';
        const method = taskId ? 'PUT' : 'POST';
        
        fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(taskData)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.error || 'Task operation failed');
                });
            }
            return response.json();
        })
        .then(updatedTask => {
            closeModal();
            loadTasks();
            
            // Reload task details if editing
            if (taskId) {
                loadTaskDetails(taskId);
            } else {
                // Auto-select newly created task
                setTimeout(() => {
                    const newTaskRow = document.querySelector('tr[data-task-id="' + updatedTask.id + '"]');
                    if (newTaskRow) {
                        newTaskRow.click();
                    }
                }, 300);
            }
            
            const message = isEditing ? 'Task updated successfully!' : 'Task created successfully!';
            // console.log('[SUBMIT_TASK]', message);
            showNotification(message, 'success');
        })
        .catch(error => {
            // console.error('[SUBMIT_TASK] Error:', error);
            const action = isEditing ? 'update' : 'create';
            showNotification('Failed to ' + action + ' task: ' + error.message, 'error');
        });
    }

    /**
     * Close modal and clean up
     */
    function closeModal() {
        // console.log('[CLOSE_MODAL] Closing modal');
        
        const modalEl = document.getElementById('taskModal');
        const modalInstance = bootstrap.Modal.getInstance(modalEl);
        
        if (modalInstance) {
            modalInstance.hide();
            
            // Remove modal backdrop manually (Bootstrap fix)
            const modalBackdrops = document.getElementsByClassName('modal-backdrop');
            for (let i = 0; i < modalBackdrops.length; i++) {
                modalBackdrops[i].remove();
            }
            
            // Reset body styles
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
        }
    }

    // ==================================================================
    // Sorting Functions
    // ==================================================================
    
    /**
     * Setup sorting event listeners for table headers
     */
    function setupSorting() {
        // console.log('[SETUP_SORTING] Setting up table sorting');
        
        document.querySelectorAll('.tasks-table th[data-sort]').forEach(th => {
            th.addEventListener('click', function() {
                const sortField = this.dataset.sort;
                
                // Toggle direction if same field, otherwise reset to ascending
                if (sortField === currentSortField) {
                    currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
                } else {
                    currentSortField = sortField;
                    currentSortDirection = 'asc';
                }
                
                // console.log('[SORT] Field:', currentSortField, 'Direction:', currentSortDirection);
                
                updateSortingUI();
                sortTasks();
                renderTasksTable(tasks);
            });
        });
    }

    /**
     * Sort tasks array based on current sort field and direction
     */
    function sortTasks() {
        tasks.sort((a, b) => {
            let valueA, valueB;
            
            // Get comparison values based on sort field
            switch(currentSortField) {
                case 'title':
                    valueA = (a.title || '').toLowerCase();
                    valueB = (b.title || '').toLowerCase();
                    break;
                    
                case 'project':
                    valueA = (a.project?.name || '').toLowerCase();
                    valueB = (b.project?.name || '').toLowerCase();
                    break;
                    
                case 'assignee':
                    valueA = ((a.assignee?.full_name || a.assignee?.username) || '').toLowerCase();
                    valueB = ((b.assignee?.full_name || b.assignee?.username) || '').toLowerCase();
                    break;
                    
                case 'priority':
                    const priorityOrder = { urgent: 0, high: 1, medium: 2, low: 3 };
                    valueA = priorityOrder[a.priority];
                    valueB = priorityOrder[b.priority];
                    break;
                    
                case 'status':
                    const statusOrder = { todo: 0, in_progress: 1, review: 2, done: 3 };
                    valueA = statusOrder[a.status];
                    valueB = statusOrder[b.status];
                    break;
                    
                case 'due_date':
                    valueA = a.due_date ? new Date(a.due_date) : new Date(0);
                    valueB = b.due_date ? new Date(b.due_date) : new Date(0);
                    break;
                    
                default:
                    valueA = (a.title || '').toLowerCase();
                    valueB = (b.title || '').toLowerCase();
            }
            
            // Handle null/undefined values
            if (valueA === null || valueA === undefined) valueA = '';
            if (valueB === null || valueB === undefined) valueB = '';
            
            // Compare values
            if (valueA < valueB) return currentSortDirection === 'asc' ? -1 : 1;
            if (valueA > valueB) return currentSortDirection === 'asc' ? 1 : -1;
            return 0;
        });
    }

    /**
     * Update UI to reflect current sorting state
     */
    function updateSortingUI() {
        // Remove sorting indicators from all headers
        document.querySelectorAll('.tasks-table th').forEach(th => {
            th.classList.remove('sorted');
            const icon = th.querySelector('i');
            if (icon) icon.className = 'bi bi-arrow-down-up';
        });
        
        // Add sorting indicator to current sorted column
        const currentTh = document.querySelector('.tasks-table th[data-sort="' + currentSortField + '"]');
        if (currentTh) {
            currentTh.classList.add('sorted');
            const icon = currentTh.querySelector('i');
            if (icon) {
                icon.className = currentSortDirection === 'asc' ? 'bi bi-arrow-down' : 'bi bi-arrow-up';
            }
        }
    }

    // ==================================================================
    // System Initialization
    // ==================================================================
    
    // console.info('[INIT] Starting initialization sequence');
    
    loadUsers();
    loadProjects();
    loadTasks();
    setupEventListeners();
    setupSorting();
    
    // console.info('[INIT] Task Management System initialized successfully');
}

// Make function globally available
window.initTaskManagement = initTaskManagement;

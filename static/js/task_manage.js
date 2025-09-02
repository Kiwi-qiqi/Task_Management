/**
 * Initializes the task management system
 * Sets up event listeners, loads initial data, and manages application state
 */
function initTaskManagement() {
    console.info('Initializing Task Management System');

    // ==================================================================
    // State
    // ==================================================================
    let tasks = [];
    let currentSortField = 'title';
    let currentSortDirection = 'asc';
    let selectedTaskId = null;
    let detailVisible = false;
    let isEditing = false;

    // ==================================================================
    // Utilities
    // ==================================================================
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
            return `${year}-${month}-${day} ${hours}:${minutes}`;
        } catch (e) {
            console.warn('Invalid date format', dateString);
            return '';
        }
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

    function populateDropdown(elementId, items, primaryField, fallbackField = null) {
        const dropdown = document.getElementById(elementId);
        if (!dropdown) return;
        while (dropdown.options.length > 1) dropdown.remove(1);
        items.forEach(item => {
            const option = document.createElement('option');
            option.value = item.id;
            option.textContent = item[primaryField] || (fallbackField && item[fallbackField]) || `Item ${item.id}`;
            dropdown.appendChild(option);
        });
    }

    function getPriorityClass(priority) {
        const p = (priority || '').toLowerCase();
        return { high: 'priority-high', medium: 'priority-medium', low: 'priority-low', urgent: 'priority-urgent' }[p] || 'priority-unknown';
    }

    function getPriorityText(priority) {
        const p = (priority || '').toLowerCase();
        return { high: 'High', medium: 'Medium', low: 'Low', urgent: 'Urgent' }[p] || 'Unknown';
    }

    function getStatusClass(status) {
        const s = (status || '').toLowerCase();
        return { todo: 'status-todo', in_progress: 'status-in_progress', review: 'status-review', done: 'status-done' }[s] || 'status-unknown';
    }

    function getStatusText(status) {
        const s = (status || '').toLowerCase();
        return { todo: 'To Do', in_progress: 'In Progress', review: 'In Review', done: 'Done' }[s] || 'Unknown';
    }

    function showErrorNotification(message) {
        console.error('Error:', message);
        alert(message);
    }

    function handleError(message) {
        return function(error) {
            console.error(message, error);
            try { showErrorNotification(message); } catch (e) { alert(message); }
        };
    }

    function showNotification(message) {
        console.log('Notification:', message);
        try { alert(message); } catch (e) { console.log(message); }
    }

    // ==================================================================
    // Data loaders
    // ==================================================================
    function loadUsers() {
        fetch('/api/users')
            .then(response => { if (!response.ok) throw new Error(`Failed to load users: ${response.status}`); return response.json(); })
            .then(users => { populateDropdown('assigneeFilter', users, 'full_name', 'username'); populateDropdown('assignee', users, 'full_name', 'username'); })
            .catch(error => { console.error('Error loading users:', error); showErrorNotification('Failed to load users. Please try again later.'); });
    }

    function loadProjects() {
        fetch('/api/projects')
            .then(response => { if (!response.ok) throw new Error(`Failed to load projects: ${response.status}`); return response.json(); })
            .then(projects => { populateDropdown('projectFilter', projects, 'name'); populateDropdown('project', projects, 'name'); })
            .catch(error => { console.error('Error loading projects:', error); showErrorNotification('Failed to load projects. Please try again later.'); });
    }

    function loadTasks() {
        const params = new URLSearchParams();
        const status = document.getElementById('statusFilter')?.value;
        const assignee = document.getElementById('assigneeFilter')?.value;
        const project = document.getElementById('projectFilter')?.value;
        const priority = document.getElementById('priorityFilter')?.value;
        const text = document.getElementById('textSearch')?.value;
        if (status && status !== 'all') params.append('status', status);
        if (assignee && assignee !== 'all') params.append('assignee', assignee);
        if (project && project !== 'all') params.append('project', project);
        if (priority && priority !== 'all') params.append('priority', priority);
        if (text) params.append('search_text', text);
        fetch(`/api/tasks?${params.toString()}`)
            .then(response => { if (!response.ok) throw new Error(`Failed to load tasks: ${response.status}`); return response.json(); })
            .then(data => { tasks = data.tasks || data; sortTasks(); renderTasksTable(tasks); })
            .catch(error => { console.error('Error loading tasks:', error); showErrorNotification('Failed to load tasks. Please try again later.'); renderTasksTable([]); });
    }

    function loadComments(taskId) {
        fetch(`/api/tasks/${taskId}/comments`, { credentials: 'same-origin' })
            .then(response => {
                if (!response.ok) {
                    const ct = response.headers.get('content-type') || '';
                    if (ct.includes('application/json')) {
                        return response.json().then(j => { throw new Error(j.error || `Failed to load comments: ${response.status}`); });
                    }
                    return response.text().then(t => { throw new Error(t || `Failed to load comments: ${response.status}`); });
                }
                const ct = response.headers.get('content-type') || '';
                if (!ct.includes('application/json')) {
                    return response.text().then(t => { throw new Error('Server returned non-JSON response'); });
                }
                return response.json();
            })
            .then(comments => renderComments(comments))
            .catch(error => { console.error('Error loading comments:', error); alert((error.message && error.message.includes('Authentication')) ? 'Authentication required. Please login.' : 'Failed to load comments. Please try again later.'); });
    }

    // ==================================================================
    // Rendering
    // ==================================================================
    function renderTasksTable(tasks) {
        const tableBody = document.getElementById('tasksTableBody');
        const tasksCount = document.getElementById('tasksCount');
        if (!tableBody || !tasksCount) return;
        tableBody.innerHTML = '';
        tasksCount.textContent = tasks.length;
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
        tasks.forEach(task => {
            const row = document.createElement('tr');
            row.dataset.taskId = task.id;
            if (selectedTaskId === task.id && detailVisible) row.classList.add('selected');
            const projectName   = task.project?.name || 'No Project';
            const assigneeName  = task.assignee?.full_name || task.assignee?.username || 'Unassigned';
            const dueDate       = task.due_date ? formatDate(task.due_date) : 'Not set';
            const priorityClass = getPriorityClass(task.priority);
            const priorityText  = getPriorityText(task.priority);
            const statusClass   = getStatusClass(task.status);
            const statusText    = getStatusText(task.status);
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

    function renderComments(comments) {
        const container = document.getElementById('commentsContainer');
        if (!container) return;
        container.innerHTML = '';
        if (!comments || comments.length === 0) { container.innerHTML = '<p class="text-muted">No comments yet</p>'; return; }
        comments.forEach(comment => {
            const commentCard = document.createElement('div');
            commentCard.className = 'comment-card';
            let formattedDate = 'Unknown date';
            try { const date = new Date(comment.created_at); formattedDate = date.toLocaleDateString('en-US', { year:'numeric', month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' }); } catch (e) { console.warn('Invalid date format for comment', comment); }
            const authorName = comment.author?.full_name || comment.author?.username || 'Unknown User';
            commentCard.innerHTML = `
                <div class="comment-header">
                    <div class="comment-author">${authorName}</div>
                    <div class="comment-date">${formattedDate}</div>
                </div>
                <div class="comment-content">${comment.content || 'No content'}</div>
            `;

            // Render attachments (if any) for this comment
            if (Array.isArray(comment.attachments) && comment.attachments.length > 0) {
                const attList = document.createElement('ul');
                attList.className = 'comment-attachments list-unstyled mt-2';
                comment.attachments.forEach(att => {
                    const li = document.createElement('li');
                    const a = document.createElement('a');
                    a.href = att.download_url || `/api/attachments/${att.id}`;
                    a.textContent = att.filename || `Attachment ${att.id}`;
                    a.target = '_blank';
                    li.appendChild(a);
                    attList.appendChild(li);
                });
                commentCard.appendChild(attList);
            }
            container.appendChild(commentCard);
        });
    }

    function loadTaskDetails(taskId) {
        const task = tasks.find(t => t.id === taskId);
        if (!task) return;
        const container = document.getElementById('taskDetailContainer');
        container.style.display = 'block';
        document.getElementById('taskDetailTitle').textContent       = task.title || 'Untitled Task';
        document.getElementById('taskDetailDescription').textContent = task.description || 'No description provided';
        document.getElementById('taskDetailStatus').className        = `status-badge ${getStatusClass(task.status)}`;
        document.getElementById('taskDetailStatus').textContent      = getStatusText(task.status);
        document.getElementById('taskDetailPriority').className      = `badge ${getPriorityClass(task.priority)}`;
        document.getElementById('taskDetailPriority').textContent    = getPriorityText(task.priority);
        document.getElementById('taskDetailType').textContent        = task.type ? task.type.charAt(0).toUpperCase() + task.type.slice(1) : 'Unknown';
        document.getElementById('taskDetailSeverity').textContent    = task.severity ? task.severity.charAt(0).toUpperCase() + task.severity.slice(1) : 'Unknown';
        document.getElementById('taskDetailCreated').textContent     = formatDate(task.created_at);
        document.getElementById('taskDetailUpdated').textContent     = formatDate(task.updated_at);
        const projectName = task.project?.name || 'No Project';
        const categoryName = task.project?.category?.name || 'No Category';
        const categoryType = task.project?.category?.type || '';
        document.getElementById('taskDetailProject').textContent = projectName;
        document.getElementById('taskDetailCategory').textContent = `${categoryName}${categoryType ? ` (${categoryType})` : ''}`;
        const assigneeName = task.assignee?.full_name || task.assignee?.username || 'Unassigned';
        document.getElementById('taskDetailAssignee').textContent  = assigneeName;
        document.getElementById('taskDetailStartDate').textContent = formatDate(task.start_date);
        document.getElementById('taskDetailDueDate').textContent   = formatDate(task.due_date);
    }

    // ==================================================================
    // Event listeners & UI actions
    // ==================================================================
    function resetFilters() {
        document.getElementById('statusFilter').value   = 'all';
        document.getElementById('assigneeFilter').value = 'all';
        document.getElementById('projectFilter').value  = 'all';
        document.getElementById('priorityFilter').value = 'all';
        document.getElementById('textSearch').value     = '';
        loadTasks();
    }

    function closeTaskDetail() {
        const scrollContainer = document.getElementById('tasksScrollContainer');
        const detailContainer = document.getElementById('taskDetailContainer');
        scrollContainer && (scrollContainer.style.maxHeight = '70vh');
        detailContainer && (detailContainer.style.display = 'none');
        if (selectedTaskId) { const selectedRow = document.querySelector(`#tasksTableBody tr[data-task-id="${selectedTaskId}"]`); selectedRow && selectedRow.classList.remove('selected'); }
        detailVisible = false; selectedTaskId = null;
    }

    function handleTaskRowClick(e) {
        const row = e.target.closest('tr'); if (!row || !row.dataset.taskId) return;
        const taskId = parseInt(row.dataset.taskId); const scrollContainer = document.getElementById('tasksScrollContainer');
        if (selectedTaskId === taskId) {
            detailVisible = !detailVisible;
            if (detailVisible) { if (scrollContainer) scrollContainer.style.maxHeight = '40vh'; document.getElementById('taskDetailContainer').style.display = 'block'; row.classList.add('selected'); }
            else { if (scrollContainer) scrollContainer.style.maxHeight = '70vh'; document.getElementById('taskDetailContainer').style.display = 'none'; row.classList.remove('selected'); }
        } else {
            selectedTaskId = taskId; detailVisible = true; document.querySelectorAll('#tasksTableBody tr').forEach(r => r.classList.remove('selected'));
            if (scrollContainer) scrollContainer.style.maxHeight = '40vh'; document.getElementById('taskDetailContainer').style.display = 'block'; row.classList.add('selected');
            loadTaskDetails(taskId); loadComments(taskId);
        }
    }

    function setupEventListeners() {
        const tableBody = document.getElementById('tasksTableBody'); if (tableBody) tableBody.addEventListener('click', handleTaskRowClick);
        ['statusFilter','assigneeFilter','projectFilter','priorityFilter'].forEach(id => { const f = document.getElementById(id); if (f) f.addEventListener('change', loadTasks); });
        const textSearch     = document.getElementById('textSearch'); if (textSearch) textSearch.addEventListener('input', debounce(loadTasks,300));
        const resetBtn       = document.getElementById('resetFilters'); if (resetBtn) resetBtn.addEventListener('click', resetFilters);
        const createBtn      = document.getElementById('createTaskBtn'); if (createBtn) createBtn.addEventListener('click', () => openTaskModal());
        const editBtn        = document.getElementById('editTaskBtn'); if (editBtn) editBtn.addEventListener('click', () => openTaskModal(selectedTaskId));
        const submitBtn      = document.getElementById('submitTaskForm'); if (submitBtn) submitBtn.addEventListener('click', handleTaskSubmission);
        const closeDetail    = document.getElementById('closeDetailBtn'); if (closeDetail) closeDetail.addEventListener('click', closeTaskDetail);
        const addCommentForm = document.getElementById('addCommentForm'); if (addCommentForm) addCommentForm.addEventListener('submit', function(e){ e.preventDefault(); addComment(); });
    }

    // ==================================================================
    // Comments
    // ==================================================================
    function addComment() {
        const commentInput = document.getElementById('commentInput');
        const comment = commentInput ? commentInput.value.trim() : '';
        if (!comment) return;

        const selectedRow = document.querySelector('#tasksTableBody tr.selected');
        if (!selectedRow) return;
        const taskId = parseInt(selectedRow.dataset.taskId);

        const filesInput = document.getElementById('commentFiles');
        const formData = new FormData();
        formData.append('content', comment);
        if (filesInput && filesInput.files && filesInput.files.length > 0) {
            for (let i = 0; i < filesInput.files.length; i++) {
                formData.append('files', filesInput.files[i]);
            }
        }

        fetch(`/api/tasks/${taskId}/comments`, { method: 'POST', body: formData, credentials: 'same-origin' })
            .then(response => {
                if (response.ok) {
                    commentInput.value = '';
                    if (filesInput) filesInput.value = '';
                    loadComments(taskId);
                } else {
                    const ct = response.headers.get('content-type') || '';
                    if (ct.includes('application/json')) {
                        return response.json().then(j => { throw new Error(j.error || 'Failed to add comment'); });
                    }
                    return response.text().then(t => { throw new Error(t || 'Failed to add comment'); });
                }
            })
            .catch(error => { console.error('Error adding comment:', error); alert('Failed to add comment. Please try again later.'); });
    }

    // ==================================================================
    // Modal & CRUD
    // ==================================================================
    function openTaskModal(taskId) {
        const modalEl = document.getElementById('taskModal'); const modal = new bootstrap.Modal(modalEl); const modalTitle = document.getElementById('taskModalLabel'); const taskIdInput = document.getElementById('taskId');
        document.getElementById('taskForm').reset(); taskIdInput.value = '';
        if (taskId) {
            isEditing = true; modalTitle.textContent = 'Edit Task'; taskIdInput.value = taskId;
            fetch(`/api/tasks/${taskId}`).then(response => { if (!response.ok) throw new Error('Failed to load task'); return response.json(); }).then(task => {
                document.getElementById('title').value       = task.title || '';
                document.getElementById('description').value = task.description || '';
                document.getElementById('type').value        = task.type || 'task';
                document.getElementById('priority').value    = task.priority || 'medium';
                document.getElementById('severity').value    = task.severity || 'normal';
                document.getElementById('status').value      = task.status || 'todo';
                const assigneeSelect = document.getElementById('assignee'); if (assigneeSelect) assigneeSelect.value = task.assignee?.id || '';
                const projectSelect = document.getElementById('project'); if (projectSelect) projectSelect.value = task.project?.id || '';
                document.getElementById('start_date').value = formatDateTimeForInput(task.start_date);
                document.getElementById('due_date').value = formatDateTimeForInput(task.due_date);
            }).catch(handleError('Failed to load task details'));
        } else { isEditing = false; modalTitle.textContent = 'Create New Task'; }
        modal.show();
    }

    function handleTaskSubmission() {
        const form       = document.getElementById('taskForm'); const formData                                           = new FormData(form); const taskId = formData.get('id');
        const taskData   = { title: formData.get('title'), description: formData.get('description'), type: formData.get('type'), status: formData.get('status'), priority: formData.get('priority'), severity: formData.get('severity'), project_id: parseInt(formData.get('project_id') || formData.get('project')) };
        const assigneeId = formData.get('assignee_id') || formData.get('assignee'); if (assigneeId) taskData.assignee_id = parseInt(assigneeId);
        const startDate  = formData.get('start_date'); if (startDate) taskData.start_date                                = new Date(startDate).toISOString();
        const dueDate    = formData.get('due_date'); if (dueDate) taskData.due_date                                      = new Date(dueDate).toISOString();
        const url        = taskId ? `/api/tasks/${taskId}` : '/api/tasks'; const method                                  = taskId ? 'PUT' : 'POST';
        fetch(url, { method: method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(taskData) })
            .then(response => { if (!response.ok) throw new Error('Task operation failed'); return response.json(); })
            .then(() => { const modalEl = document.getElementById('taskModal'); const modalInstance = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl); modalInstance.hide(); loadTasks(); if (taskId && selectedTaskId === parseInt(taskId)) loadTaskDetails(selectedTaskId); showNotification(isEditing ? 'Task updated successfully!' : 'Task created successfully!'); })
            .catch(handleError(isEditing ? 'Failed to update task' : 'Failed to create task'));
    }

    // ==================================================================
    // Sorting
    // ==================================================================
    function setupSorting() {
        document.querySelectorAll('.tasks-table th[data-sort]').forEach(th => {
            th.addEventListener('click', function() {
                const sortField = this.dataset.sort;
                if (sortField === currentSortField) currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
                else { currentSortField = sortField; currentSortDirection = 'asc'; }
                updateSortingUI(); sortTasks(); renderTasksTable(tasks);
            });
        });
    }

    function sortTasks() {
        tasks.sort((a, b) => {
            let valueA, valueB;
            switch(currentSortField) {
                case 'title'   : valueA = (a.title||'').toLowerCase(); valueB = (b.title||'').toLowerCase(); break;
                case 'project' : valueA = (a.project?.name||'').toLowerCase(); valueB = (b.project?.name||'').toLowerCase(); break;
                case 'assignee': valueA = ((a.assignee?.full_name||a.assignee?.username)||'').toLowerCase(); valueB = ((b.assignee?.full_name||b.assignee?.username)||'').toLowerCase(); break;
                case 'priority': { const priorityOrder = {urgent:0, high:1, medium:2, low:3}; valueA = priorityOrder[a.priority]; valueB = priorityOrder[b.priority]; break; }
                case 'status'  : { const statusOrder = {todo:0, in_progress:1, review:2, done:3}; valueA = statusOrder[a.status]; valueB = statusOrder[b.status]; break; }
                case 'due_date': valueA = a.due_date ? new Date(a.due_date): new Date(0); valueB = b.due_date ? new Date(b.due_date): new Date(0); break;
                default: valueA = (a.title||'').toLowerCase(); valueB = (b.title||'').toLowerCase();
            }
            if (valueA === null || valueA === undefined) valueA = ''; if (valueB === null || valueB === undefined) valueB = '';
            if (valueA < valueB) return currentSortDirection === 'asc' ? -1 : 1; if (valueA > valueB) return currentSortDirection === 'asc' ? 1 : -1; return 0;
        });
    }

    function updateSortingUI() {
        document.querySelectorAll('.tasks-table th').forEach(th => { th.classList.remove('sorted'); const icon = th.querySelector('i'); if (icon) icon.className = 'bi bi-arrow-down-up'; });
        const currentTh = document.querySelector(`.tasks-table th[data-sort="${currentSortField}"]`);
        if (currentTh) { currentTh.classList.add('sorted'); const icon = currentTh.querySelector('i'); if (icon) icon.className = currentSortDirection === 'asc' ? 'bi bi-arrow-down' : 'bi bi-arrow-up'; }
    }

    // ==================================================================
    // Initialization
    // ==================================================================
    loadUsers(); loadProjects(); loadTasks(); setupEventListeners(); setupSorting();
}

// Ensure the initializer is available globally
window.initTaskManagement = initTaskManagement;
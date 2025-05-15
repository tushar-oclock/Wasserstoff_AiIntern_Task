document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const uploadForm = document.getElementById('uploadForm');
    const documentFiles = document.getElementById('documentFiles');
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadProgress = document.getElementById('uploadProgress');
    const uploadStatus = document.getElementById('uploadStatus');
    const documentList = document.getElementById('documentList');
    const documentCount = document.getElementById('documentCount');
    const selectAllBtn = document.getElementById('selectAllBtn');
    const clearSelectionBtn = document.getElementById('clearSelectionBtn');
    const queryInput = document.getElementById('queryInput');
    const submitQueryBtn = document.getElementById('submitQueryBtn');
    const responseSection = document.getElementById('responseSection');
    const loadingResults = document.getElementById('loadingResults');
    const themesContainer = document.getElementById('themesContainer');
    const synthesizedResponseContent = document.getElementById('synthesizedResponseContent');
    const responsesTableBody = document.getElementById('responsesTableBody');
    const toggleViewBtn = document.getElementById('toggleViewBtn');
    const exportBtn = document.getElementById('exportBtn');
    const themeChart = document.getElementById('themeChart');

    // State
    let documents = [];
    let selectedDocuments = [];
    let currentQueryResults = null;
    let themeChartInstance = null;

    // Initialize
    fetchDocuments();

    // Event Listeners
    uploadForm.addEventListener('submit', handleDocumentUpload);
    selectAllBtn.addEventListener('click', selectAllDocuments);
    clearSelectionBtn.addEventListener('click', clearDocumentSelection);
    submitQueryBtn.addEventListener('click', submitQuery);
    toggleViewBtn.addEventListener('click', toggleResponseView);
    exportBtn.addEventListener('click', exportResults);

    // Functions
    function handleDocumentUpload(event) {
        event.preventDefault();
        
        const files = documentFiles.files;
        if (files.length === 0) {
            showAlert(uploadStatus, 'Please select at least one file', 'danger');
            return;
        }

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files[]', files[i]);
        }

        // Show progress
        uploadProgress.classList.remove('d-none');
        uploadProgress.querySelector('.progress-bar').style.width = '0%';
        uploadBtn.disabled = true;
        showAlert(uploadStatus, 'Uploading documents...', 'info');

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            uploadProgress.querySelector('.progress-bar').style.width = '100%';
            return response.json();
        })
        .then(data => {
            if (data.success) {
                const successCount = data.documents.length;
                const errorCount = data.errors.length;
                
                let message = `Successfully uploaded ${successCount} document(s).`;
                let alertType = 'success';
                
                if (errorCount > 0) {
                    message += ` Failed to upload ${errorCount} document(s).`;
                    alertType = 'warning';
                }
                
                showAlert(uploadStatus, message, alertType);
                uploadForm.reset();
                fetchDocuments();
            } else {
                showAlert(uploadStatus, 'Failed to upload documents', 'danger');
            }
        })
        .catch(error => {
            showAlert(uploadStatus, `Error: ${error.message}`, 'danger');
        })
        .finally(() => {
            uploadBtn.disabled = false;
            setTimeout(() => {
                uploadProgress.classList.add('d-none');
            }, 1000);
        });
    }

    function fetchDocuments() {
        fetch('/documents')
            .then(response => response.json())
            .then(data => {
                documents = data.documents || [];
                renderDocumentList();
                updateDocumentCount();
            })
            .catch(error => {
                console.error('Error fetching documents:', error);
                showAlert(uploadStatus, `Error fetching documents: ${error.message}`, 'danger');
            });
    }

    function renderDocumentList() {
        if (documents.length === 0) {
            documentList.innerHTML = `
                <div class="text-center py-5 text-muted">
                    <i class="fas fa-file-upload fa-3x mb-3"></i>
                    <p>Upload documents to get started</p>
                </div>
            `;
            return;
        }

        documentList.innerHTML = '';
        documents.forEach(doc => {
            const isSelected = selectedDocuments.includes(doc.id);
            const docElement = document.createElement('div');
            docElement.className = `document-item p-2 mb-2 rounded ${isSelected ? 'selected' : ''}`;
            docElement.dataset.id = doc.id;
            
            // Determine icon based on filename extension
            let icon = 'fas fa-file';
            const ext = doc.filename.split('.').pop().toLowerCase();
            if (['pdf'].includes(ext)) icon = 'fas fa-file-pdf';
            else if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'].includes(ext)) icon = 'fas fa-file-image';
            else if (['txt', 'md', 'csv'].includes(ext)) icon = 'fas fa-file-alt';
            
            docElement.innerHTML = `
                <div class="d-flex align-items-center">
                    <div class="form-check">
                        <input class="form-check-input document-checkbox" type="checkbox" value="${doc.id}" id="doc-${doc.id}" ${isSelected ? 'checked' : ''}>
                        <label class="form-check-label" for="doc-${doc.id}"></label>
                    </div>
                    <div class="ms-2 me-auto">
                        <div class="d-flex align-items-center">
                            <i class="${icon} me-2 text-muted"></i>
                            <span class="text-truncate" style="max-width: 180px;" title="${doc.filename}">${doc.filename}</span>
                        </div>
                        <small class="text-muted">${doc.page_count || 'Unknown'} pages</small>
                    </div>
                </div>
            `;
            
            documentList.appendChild(docElement);
            
            // Add event listener to checkbox
            const checkbox = docElement.querySelector('.document-checkbox');
            checkbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    selectedDocuments.push(doc.id);
                } else {
                    selectedDocuments = selectedDocuments.filter(id => id !== doc.id);
                }
                docElement.classList.toggle('selected', e.target.checked);
            });
        });
    }

    function updateDocumentCount() {
        documentCount.textContent = `${documents.length} document${documents.length !== 1 ? 's' : ''}`;
    }

    function selectAllDocuments() {
        selectedDocuments = documents.map(doc => doc.id);
        document.querySelectorAll('.document-checkbox').forEach(checkbox => {
            checkbox.checked = true;
        });
        document.querySelectorAll('.document-item').forEach(item => {
            item.classList.add('selected');
        });
    }

    function clearDocumentSelection() {
        selectedDocuments = [];
        document.querySelectorAll('.document-checkbox').forEach(checkbox => {
            checkbox.checked = false;
        });
        document.querySelectorAll('.document-item').forEach(item => {
            item.classList.remove('selected');
        });
    }

    function submitQuery() {
        const query = queryInput.value.trim();
        if (!query) {
            alert('Please enter a query');
            return;
        }

        if (documents.length === 0) {
            alert('Please upload at least one document first');
            return;
        }

        // If no documents selected, use all documents
        const docsToQuery = selectedDocuments.length > 0 ? selectedDocuments : documents.map(doc => doc.id);

        // Show loading
        responseSection.classList.remove('d-none');
        loadingResults.classList.remove('d-none');
        themesContainer.innerHTML = '';
        synthesizedResponseContent.innerHTML = '';
        responsesTableBody.innerHTML = '';
        
        // Scroll to results
        responseSection.scrollIntoView({ behavior: 'smooth' });

        // Send query
        fetch('/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                documentIds: docsToQuery
            })
        })
        .then(response => response.json())
        .then(data => {
            currentQueryResults = data;
            renderQueryResults(data);
        })
        .catch(error => {
            console.error('Error submitting query:', error);
            synthesizedResponseContent.innerHTML = `
                <div class="alert alert-danger">
                    Error processing query: ${error.message}
                </div>
            `;
        })
        .finally(() => {
            loadingResults.classList.add('d-none');
        });
    }

    function renderQueryResults(data) {
        // Render themes
        renderThemes(data.themes);
        
        // Render synthesized response
        renderSynthesizedResponse(data.synthesized_response);
        
        // Render document responses
        renderDocumentResponses(data.document_responses);
        
        // Render theme chart
        renderThemeChart(data.themes);
    }

    function renderThemes(themes) {
        if (!themes || themes.length === 0) {
            themesContainer.innerHTML = '<div class="alert alert-info">No themes identified in the documents.</div>';
            return;
        }

        themesContainer.innerHTML = '';
        themes.forEach(theme => {
            const themeElement = document.createElement('div');
            themeElement.className = 'theme-item card mb-3';
            themeElement.innerHTML = `
                <div class="card-body">
                    <h6 class="card-title">${theme.name}</h6>
                    <p class="card-text">${theme.description}</p>
                    <div class="supporting-docs">
                        ${theme.supporting_docs.map(docId => {
                            const doc = documents.find(d => d.id === docId);
                            return doc ? `<span class="badge bg-secondary me-1" title="${doc.filename}">${docId}</span>` : '';
                        }).join('')}
                    </div>
                </div>
            `;
            themesContainer.appendChild(themeElement);
        });
    }

    function renderSynthesizedResponse(response) {
        if (!response) {
            synthesizedResponseContent.innerHTML = '<div class="alert alert-warning">No synthesized response available.</div>';
            return;
        }
        
        if (response.synthesized_response) {
            synthesizedResponseContent.innerHTML = `<div>${formatResponseText(response.synthesized_response)}</div>`;
        } else if (response.themes_analysis) {
            let html = '';
            response.themes_analysis.forEach(theme => {
                html += `
                    <div class="mb-3">
                        <h6 class="text-primary">${theme.theme_name}</h6>
                        <p>${formatResponseText(theme.explanation)}</p>
                        <p><strong>Evidence:</strong> ${formatResponseText(theme.supporting_evidence)}</p>
                        <p><small class="text-muted">${formatResponseText(theme.relevance_to_query)}</small></p>
                    </div>
                `;
            });
            synthesizedResponseContent.innerHTML = html;
        } else {
            synthesizedResponseContent.innerHTML = formatResponseText(JSON.stringify(response));
        }
    }

    function renderDocumentResponses(responses) {
        if (!responses || responses.length === 0) {
            responsesTableBody.innerHTML = '<tr><td colspan="3" class="text-center">No document responses available.</td></tr>';
            return;
        }

        responsesTableBody.innerHTML = '';
        responses.forEach(response => {
            const row = document.createElement('tr');
            
            // Document column
            const docCell = document.createElement('td');
            docCell.innerHTML = `
                <div>
                    <strong>${response.filename}</strong><br>
                    <small class="text-muted">ID: ${response.id}</small>
                </div>
            `;
            
            // Response column
            const responseCell = document.createElement('td');
            responseCell.innerHTML = formatResponseText(response.response);
            
            // Citations column
            const citationsCell = document.createElement('td');
            if (response.citations && response.citations.length > 0) {
                const citationsHtml = response.citations.map(citation => 
                    `<div class="citation-item">
                        <div class="location text-info">${citation.location}</div>
                        <div class="text small">"${citation.text}"</div>
                    </div>`
                ).join('');
                citationsCell.innerHTML = citationsHtml;
            } else {
                citationsCell.textContent = 'No specific citations';
            }
            
            row.appendChild(docCell);
            row.appendChild(responseCell);
            row.appendChild(citationsCell);
            responsesTableBody.appendChild(row);
        });
    }

    function renderThemeChart(themes) {
        if (!themes || themes.length === 0) return;
        
        // Destroy previous chart if exists
        if (themeChartInstance) {
            themeChartInstance.destroy();
        }
        
        // Prepare data for the chart
        const labels = themes.map(theme => theme.name);
        const data = themes.map(theme => theme.supporting_docs.length);
        const colors = generateColors(themes.length);
        
        // Create chart
        themeChartInstance = new Chart(themeChart, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#fff'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Theme Distribution',
                        color: '#fff'
                    }
                }
            }
        });
    }

    function toggleResponseView() {
        const isTableView = toggleViewBtn.innerHTML.includes('table');
        
        if (isTableView) {
            // Switch to card view
            toggleViewBtn.innerHTML = '<i class="fas fa-table me-1"></i> Show Table';
            responsesTableBody.parentElement.parentElement.classList.add('d-none');
            
            // Create card view
            const cardContainer = document.createElement('div');
            cardContainer.id = 'responsesCardView';
            cardContainer.className = 'row g-3';
            
            if (currentQueryResults && currentQueryResults.document_responses) {
                currentQueryResults.document_responses.forEach(response => {
                    const card = document.createElement('div');
                    card.className = 'col-md-6';
                    card.innerHTML = `
                        <div class="card h-100">
                            <div class="card-header">
                                <strong>${response.filename}</strong>
                                <small class="text-muted d-block">ID: ${response.id}</small>
                            </div>
                            <div class="card-body">
                                <div class="response-text mb-3">
                                    ${formatResponseText(response.response)}
                                </div>
                                <h6 class="small fw-bold">Citations:</h6>
                                <div class="citations small">
                                    ${response.citations && response.citations.length > 0 
                                        ? response.citations.map(citation => 
                                            `<div class="citation-item mb-2">
                                                <div class="location text-info">${citation.location}</div>
                                                <div class="text fst-italic">"${citation.text}"</div>
                                            </div>`
                                        ).join('')
                                        : 'No specific citations'
                                    }
                                </div>
                            </div>
                        </div>
                    `;
                    cardContainer.appendChild(card);
                });
            }
            
            document.getElementById('documentResponses').appendChild(cardContainer);
        } else {
            // Switch to table view
            toggleViewBtn.innerHTML = '<i class="fas fa-th me-1"></i> Show Cards';
            responsesTableBody.parentElement.parentElement.classList.remove('d-none');
            
            // Remove card view
            const cardView = document.getElementById('responsesCardView');
            if (cardView) cardView.remove();
        }
    }

    function exportResults() {
        if (!currentQueryResults) {
            alert('No results to export');
            return;
        }
        
        const exportData = {
            query: queryInput.value.trim(),
            timestamp: new Date().toISOString(),
            themes: currentQueryResults.themes,
            synthesized_response: currentQueryResults.synthesized_response,
            document_responses: currentQueryResults.document_responses
        };
        
        const jsonString = JSON.stringify(exportData, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `research-results-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // Utility Functions
    function showAlert(element, message, type) {
        element.innerHTML = `<div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>`;
        
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            const alert = element.querySelector('.alert');
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    }

    function formatResponseText(text) {
        if (!text) return '';
        
        // Convert line breaks to <br>
        let formatted = text.replace(/\n/g, '<br>');
        
        // Highlight citations [DOC001]
        formatted = formatted.replace(/\[(DOC\d+)\]/g, '<span class="badge bg-secondary">$1</span>');
        
        // Highlight citations [Page X, Paragraph Y]
        formatted = formatted.replace(/\[(Page \d+(?:, Paragraph \d+)?)\]/g, '<span class="badge bg-info">$1</span>');
        
        return formatted;
    }

    function generateColors(count) {
        const baseColors = [
            '#0d6efd', // blue
            '#6610f2', // indigo
            '#6f42c1', // purple
            '#d63384', // pink
            '#dc3545', // red
            '#fd7e14', // orange
            '#ffc107', // yellow
            '#198754', // green
            '#20c997', // teal
            '#0dcaf0'  // cyan
        ];
        
        const colors = [];
        for (let i = 0; i < count; i++) {
            colors.push(baseColors[i % baseColors.length]);
        }
        
        return colors;
    }
});

// Implementing JS

// Wait for the document to be fully loaded before attaching event listeners
document.addEventListener('DOMContentLoaded', function() {
    const taskContainer = document.querySelector('#task-container'); // Parent container for tasks

    // Event delegation for delete task confirmation and edit task functionality
    taskContainer.addEventListener('submit', handleDeleteConfirmation);
    taskContainer.addEventListener('click', handleEditTask);
});

/**
 * Handles the task deletion confirmation.
 * Prevents the deletion if the user does not confirm.
 * @param {Event} event - The event object.
 */
function handleDeleteConfirmation(event) {
    if (event.target.classList.contains('delete-form')) {
        const confirmation = confirm('Are you sure you want to delete this task?');
        if (!confirmation) {
            event.preventDefault(); // Prevent form submission if the user cancels
        }
    }
}

/**
 * Handles inline editing of tasks (either description or priority).
 * It allows users to click the edit button and update the task directly in the UI.
 * @param {Event} event - The event object.
 */
function handleEditTask(event) {
    const editButton = event.target.closest('.edit-btn');
    if (editButton) {
        const taskId = editButton.getAttribute('data-task-id');
        const field = editButton.getAttribute('data-field');
        const taskElement = document.getElementById(`task-${taskId}`);
        const targetElement = taskElement.querySelector(`.task-${field}`);
        const currentValue = targetElement.textContent;

        // Create an input field for editing
        const inputField = createInputField(field, currentValue);

        // Replace the current content with the input field
        targetElement.innerHTML = '';
        targetElement.appendChild(inputField);

        // Focus and accessibility
        inputField.focus();
        inputField.setAttribute('tabindex', '0');
        inputField.setAttribute('aria-label', `Edit ${field}`);

        // Handle the blur event
        inputField.addEventListener('blur', function() {
            const newValue = inputField.value.trim();
            if (newValue && newValue !== currentValue) {
                updateElementContent(targetElement, newValue);
                updateTask(taskId, field, newValue, targetElement, currentValue);
            } else {
                updateElementContent(targetElement, currentValue); // Revert to original
            }
        });

        // Handle the Enter key press event to save changes
        inputField.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault(); // Prevent form submission
                const newValue = inputField.value.trim();
                if (newValue && newValue !== currentValue) {
                    updateElementContent(targetElement, newValue);
                    updateTask(taskId, field, newValue, targetElement, currentValue);
                } else {
                    updateElementContent(targetElement, currentValue); // Revert to original
                }
            }
        });
    }
}

/**
 * Creates an input field for editing a task's field.
 * @param {string} field - The field being edited.
 * @param {string} currentValue - The current value of the field.
 * @returns {HTMLElement} The input field element.
 */
function createInputField(field, currentValue) {
    const inputField = document.createElement('input');
    inputField.type = field === 'priority' ? 'number' : 'text';
    inputField.value = currentValue;

    if (field === 'priority') {
        inputField.min = 1;
        inputField.max = 5;

        // Prevent invalid input
        inputField.addEventListener('keypress', function(event) {
            const char = String.fromCharCode(event.which);
            const newValue = inputField.value + char;

            if (!/^[1-5]$/.test(newValue)) {
                event.preventDefault();
            }
        });
    }

    return inputField;
}

/**
 * Sends the updated task value to the server and handles the response.
 * @param {string} taskId - The ID of the task being updated.
 * @param {string} field - The field being updated.
 * @param {string} newValue - The new value to be updated.
 * @param {HTMLElement} targetElement - The element to update with the new value.
 * @param {string} currentValue - The original value of the field.
 */
async function updateTask(taskId, field, newValue, targetElement, currentValue) {
    try {
        const response = await fetch(`/tasks/${taskId}/edit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                field,
                value: newValue
            }),
        });

        if (!response.ok) {
            throw new Error('Failed to update task');
        }

        const data = await response.json();
        if (data.success) {
            createFlashMessage(data.message, 'success');
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        createFlashMessage(error.message, 'error');
        updateElementContent(targetElement, currentValue); // Revert changes
    }
}

/**
 * Updates the content of an element.
 * @param {HTMLElement} element - The element to update.
 * @param {string} content - The new content.
 */
function updateElementContent(element, content) {
    element.textContent = content;
}

/**
 * Creates and displays a flash message.
 * @param {string} message - The message to display.
 * @param {string} type - The type of message ('success' or 'error').
 */
function createFlashMessage(message, type) {
    const flashContainer = document.querySelector('#flash-alerts');

    // Clear any existing flash messages to avoid duplication (ChatGPT helped)
    flashContainer.innerHTML = '';

    const flashMessage = document.createElement('div');
    flashMessage.classList.add('alert', `alert-${type}`);
    flashMessage.textContent = message;
    flashContainer.appendChild(flashMessage);

    // Remove the flash message after 2 seconds
    setTimeout(() => flashMessage.remove(), 2000);
}

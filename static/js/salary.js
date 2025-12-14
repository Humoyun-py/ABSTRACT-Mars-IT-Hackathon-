// ==================== SALARY MANAGEMENT PAGE ====================

// Calculate and display statistics
function calculateStatistics() {
    const rows = document.querySelectorAll('#employeeTableBody tr');
    let totalPayroll = 0;
    let totalBonuses = 0;
    let totalDeductions = 0;

    rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        const baseSalary = parseFloat(cells[3].textContent.replace(/[^0-9.-]+/g, '')) || 0;
        const bonuses = parseFloat(cells[4].textContent.replace(/[^0-9.-]+/g, '')) || 0;
        const deductions = parseFloat(cells[5].textContent.replace(/[^0-9.-]+/g, '')) || 0;
        const currentSalary = parseFloat(cells[6].textContent.replace(/[^0-9.-]+/g, '')) || 0;

        totalPayroll += currentSalary;
        totalBonuses += bonuses;
        totalDeductions += deductions;
    });

    document.getElementById('totalPayroll').textContent = totalPayroll.toLocaleString('uz-UZ') + ' UZS';
    document.getElementById('totalBonuses').textContent = totalBonuses.toLocaleString('uz-UZ') + ' UZS';
    document.getElementById('totalDeductions').textContent = totalDeductions.toLocaleString('uz-UZ') + ' UZS';
}

// Search functionality
document.getElementById('searchInput')?.addEventListener('input', (e) => {
    const searchTerm = e.target.value.toLowerCase();
    const rows = document.querySelectorAll('#employeeTableBody tr');

    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchTerm) ? '' : 'none';
    });
});

// Modal functions
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Bonus modal
function openBonusModal(employeeId, employeeName) {
    document.getElementById('bonusEmployeeId').value = employeeId;
    document.getElementById('bonusEmployeeName').value = employeeName;
    document.getElementById('bonusAmount').value = '';
    document.getElementById('bonusReason').value = '';
    openModal('bonusModal');
}

document.getElementById('bonusForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const employeeId = document.getElementById('bonusEmployeeId').value;
    const amount = document.getElementById('bonusAmount').value;
    const reason = document.getElementById('bonusReason').value || 'Premia';

    try {
        const response = await fetch(`/api/employees/${employeeId}/salary/bonus`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ amount: parseFloat(amount), reason })
        });

        const result = await response.json();

        if (result.success) {
            showNotification('✅ Premia qo\'shildi!', 'success');
            closeModal('bonusModal');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification('❌ Xatolik: ' + result.error, 'error');
        }
    } catch (error) {
        showNotification('❌ Server xatosi', 'error');
    }
});

// Deduction modal
function openDeductionModal(employeeId, employeeName) {
    document.getElementById('deductionEmployeeId').value = employeeId;
    document.getElementById('deductionEmployeeName').value = employeeName;
    document.getElementById('deductionAmount').value = '';
    document.getElementById('deductionReason').value = '';
    openModal('deductionModal');
}

document.getElementById('deductionForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const employeeId = document.getElementById('deductionEmployeeId').value;
    const amount = document.getElementById('deductionAmount').value;
    const reason = document.getElementById('deductionReason').value;

    try {
        const response = await fetch(`/api/employees/${employeeId}/salary/deduction`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ amount: parseFloat(amount), reason })
        });

        const result = await response.json();

        if (result.success) {
            showNotification('✅ Maoshdan ayirildi!', 'success');
            closeModal('deductionModal');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification('❌ Xatolik: ' + result.error, 'error');
        }
    } catch (error) {
        showNotification('❌ Server xatosi', 'error');
    }
});

// Base salary modal
function openBaseSalaryModal(employeeId, employeeName, currentBase) {
    document.getElementById('baseSalaryEmployeeId').value = employeeId;
    document.getElementById('baseSalaryEmployeeName').value = employeeName;
    document.getElementById('baseSalaryAmount').value = currentBase;
    document.getElementById('baseSalaryReason').value = '';
    openModal('baseSalaryModal');
}

document.getElementById('baseSalaryForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const employeeId = document.getElementById('baseSalaryEmployeeId').value;
    const amount = document.getElementById('baseSalaryAmount').value;
    const reason = document.getElementById('baseSalaryReason').value || 'Asosiy maosh o\'zgarishi';

    try {
        const response = await fetch(`/api/employees/${employeeId}/salary/base`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ amount: parseFloat(amount), reason })
        });

        const result = await response.json();

        if (result.success) {
            showNotification('✅ Asosiy maosh yangilandi!', 'success');
            closeModal('baseSalaryModal');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification('❌ Xatolik: ' + result.error, 'error');
        }
    } catch (error) {
        showNotification('❌ Server xatosi', 'error');
    }
});

// View history
async function viewHistory(employeeId, employeeName) {
    document.getElementById('historyEmployeeName').textContent = employeeName;
    const historyContent = document.getElementById('historyContent');
    historyContent.innerHTML = '<p style="text-align: center; padding: 2rem;">⏳ Yuklanmoqda...</p>';

    openModal('historyModal');

    try {
        const response = await fetch(`/api/employees/${employeeId}/salary/history`);
        const transactions = await response.json();

        if (transactions.length === 0) {
            historyContent.innerHTML = '<p style="text-align: center; padding: 2rem; color: #6B7280;">📭 Hali tranzaksiyalar yo\'q</p>';
            return;
        }

        let html = '<div class="timeline">';
        transactions.forEach(t => {
            const date = new Date(t.created_at).toLocaleString('uz-UZ');
            const typeIcons = {
                'bonus': '💰',
                'deduction': '⚠️',
                'base_change': '⚙️',
                'adjustment': '📝'
            };
            const icon = typeIcons[t.transaction_type] || '📋';
            const typeNames = {
                'bonus': 'Premia',
                'deduction': 'Ayirish',
                'base_change': 'Asosiy maosh',
                'adjustment': 'Tuzatish'
            };
            const typeName = typeNames[t.transaction_type] || t.transaction_type;

            html += `
                <div class="timeline-item">
                    <div class="timeline-icon">${icon}</div>
                    <div class="timeline-content">
                        <div class="timeline-header">
                            <strong>${typeName}</strong>
                            <span class="timeline-date">${date}</span>
                        </div>
                        <div class="timeline-body">
                            <p><strong>Summa:</strong> ${t.amount.toLocaleString('uz-UZ')} UZS</p>
                            <p><strong>Sabab:</strong> ${t.reason || '-'}</p>
                            <p><strong>Oldingi:</strong> ${(t.previous_salary || 0).toLocaleString('uz-UZ')} → <strong>Yangi:</strong> ${(t.new_salary || 0).toLocaleString('uz-UZ')}</p>
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';

        historyContent.innerHTML = html;
    } catch (error) {
        historyContent.innerHTML = '<p style="text-align: center; padding: 2rem; color: #DC2626;">❌ Yuklashda xatolik</p>';
    }
}

// Close modals on outside click
window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.style.display = 'none';
    }
});

// Calculate statistics on load
document.addEventListener('DOMContentLoaded', calculateStatistics);

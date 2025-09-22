import React, { useState, useEffect } from 'react';
import api from '../api';

const EmployeesList = () => {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchEmployees();
  }, []);

  const fetchEmployees = async () => {
    try {
      const response = await api.get('/employees/');
      setEmployees(response.data);
    } catch (error) {
      setError('Failed to fetch employees');
      console.error('Error fetching employees:', error);
    } finally {
      setLoading(false);
    }
  };

  const maskCNIC = (cnic) => {
    if (!cnic) return 'N/A';
    return cnic.substring(0, 6) + '***-***' + cnic.substring(12);
  };

  const getEligibilityBadge = (isEligible, score) => {
    const variant = isEligible ? 'success' : 'danger';
    const text = isEligible ? 'Eligible' : 'Ineligible';
    return (
      <span className={`badge bg-${variant}`}>
        {text} ({score.toFixed(2)})
      </span>
    );
  };

  if (loading) {
    return <div className="text-center"><div className="spinner-border"></div></div>;
  }

  return (
    <div className="container-fluid">
      <h2>Employees Management</h2>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="card">
        <div className="card-body">
          <div className="table-responsive">
            <table className="table table-striped">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>CNIC</th>
                  <th>Father's Name</th>
                  <th>Grade</th>
                  <th>Designation</th>
                  <th>Mobile</th>
                  <th>Eligibility</th>
                  <th>Fraud Flag</th>
                </tr>
              </thead>
              <tbody>
                {employees.map((employee) => (
                  <tr key={employee.id}>
                    <td>{employee.id}</td>
                    <td>{employee.name}</td>
                    <td>{maskCNIC(employee.cnic)}</td>
                    <td>{employee.father_name}</td>
                    <td>{employee.grade}</td>
                    <td>{employee.designation || 'N/A'}</td>
                    <td>{employee.mobile}</td>
                    <td>
                      {getEligibilityBadge(employee.is_eligible, employee.eligibility_score)}
                    </td>
                    <td>
                      {employee.fraud_flag ? (
                        <span className="badge bg-danger">Flagged</span>
                      ) : (
                        <span className="badge bg-success">Clean</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmployeesList;
import React, { useState, useEffect } from 'react';
import api from '../api';

const MLFlags = () => {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchFlaggedEmployees();
  }, []);

  const fetchFlaggedEmployees = async () => {
    try {
      const response = await api.get('/employees/');
      const flagged = response.data.filter(emp => emp.fraud_flag);
      setEmployees(flagged);
    } catch (error) {
      setError('Failed to fetch flagged employees');
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const maskCNIC = (cnic) => {
    if (!cnic) return 'N/A';
    return cnic.substring(0, 6) + '***-***' + cnic.substring(12);
  };

  if (loading) {
    return <div className="text-center"><div className="spinner-border"></div></div>;
  }

  return (
    <div className="container-fluid">
      <h2>ML Flags & Fraud Detection</h2>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="row">
        <div className="col-md-12">
          <div className="card">
            <div className="card-header">
              <h5>Flagged Employees (Fraud Detection)</h5>
            </div>
            <div className="card-body">
              {employees.length === 0 ? (
                <p className="text-success">No flagged employees found. All systems clean!</p>
              ) : (
                <div className="table-responsive">
                  <table className="table table-striped">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>CNIC</th>
                        <th>Father's Name</th>
                        <th>Grade</th>
                        <th>Eligibility Score</th>
                        <th>Status</th>
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
                          <td>
                            <span className={`badge bg-${employee.eligibility_score > 0.7 ? 'success' : employee.eligibility_score > 0.4 ? 'warning' : 'danger'}`}>
                              {employee.eligibility_score.toFixed(2)}
                            </span>
                          </td>
                          <td>
                            <span className="badge bg-danger">Fraud Flagged</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="row mt-4">
        <div className="col-md-6">
          <div className="card">
            <div className="card-header">
              <h5>Fraud Detection Model</h5>
            </div>
            <div className="card-body">
              <p><strong>Algorithm:</strong> Isolation Forest</p>
              <p><strong>Features:</strong></p>
              <ul>
                <li>Donation amount patterns</li>
                <li>Frequency of donations</li>
                <li>Amount variance</li>
                <li>Time since last donation</li>
              </ul>
              <p><strong>Threshold:</strong> 20% contamination rate</p>
            </div>
          </div>
        </div>

        <div className="col-md-6">
          <div className="card">
            <div className="card-header">
              <h5>Eligibility Prediction Model</h5>
            </div>
            <div className="card-body">
              <p><strong>Algorithm:</strong> Random Forest Classifier</p>
              <p><strong>Features:</strong></p>
              <ul>
                <li>Employee grade</li>
                <li>Family size</li>
                <li>Income estimate</li>
                <li>Previous aid count</li>
              </ul>
              <p><strong>Accuracy:</strong> 85%+ on synthetic data</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MLFlags;
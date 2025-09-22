import React, { useState, useEffect } from 'react';
import api from '../api';

const DistributionGenerator = () => {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchRuns();
  }, []);

  const fetchRuns = async () => {
    try {
      const response = await api.get('/admin/distribution/runs');
      setRuns(response.data);
    } catch (error) {
      setError('Failed to fetch distribution runs');
      console.error('Error fetching runs:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateDistribution = async () => {
    setGenerating(true);
    setError('');

    try {
      // Use tomorrow's date as default
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const runDate = tomorrow.toISOString().split('T')[0];

      const response = await api.post(`/admin/distribution/run?run_date=${runDate}`);

      // Refresh the list
      await fetchRuns();

      alert('Distribution generated successfully!');
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to generate distribution');
    } finally {
      setGenerating(false);
    }
  };

  const approveDistribution = async (runId) => {
    try {
      await api.post(`/admin/distribution/approve?run_id=${runId}`);
      await fetchRuns();
      alert('Distribution approved and notifications sent!');
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to approve distribution');
    }
  };

  const getStatusBadge = (status) => {
    const variants = {
      'pending': 'warning',
      'approved': 'success',
      'completed': 'info'
    };
    return (
      <span className={`badge bg-${variants[status] || 'secondary'}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  if (loading) {
    return <div className="text-center"><div className="spinner-border"></div></div>;
  }

  return (
    <div className="container-fluid">
      <h2>Distribution Management</h2>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="row">
        <div className="col-md-12">
          <div className="card">
            <div className="card-header">
              <h5 className="mb-0">Generate New Distribution</h5>
            </div>
            <div className="card-body">
              <button
                className="btn btn-primary"
                onClick={generateDistribution}
                disabled={generating}
              >
                {generating ? 'Generating...' : 'Generate Provisional Distribution'}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="row mt-4">
        <div className="col-md-12">
          <div className="card">
            <div className="card-header">
              <h5 className="mb-0">Distribution Runs</h5>
            </div>
            <div className="card-body">
              <div className="table-responsive">
                <table className="table table-striped">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Date</th>
                      <th>Status</th>
                      <th>Beneficiaries</th>
                      <th>Total Amount</th>
                      <th>Created</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.map((run) => (
                      <tr key={run.id}>
                        <td>{run.id}</td>
                        <td>{new Date(run.run_date).toLocaleDateString()}</td>
                        <td>{getStatusBadge(run.status)}</td>
                        <td>{run.total_beneficiaries}</td>
                        <td>Rs {run.total_amount.toLocaleString()}</td>
                        <td>{new Date(run.created_at).toLocaleDateString()}</td>
                        <td>
                          {run.status === 'pending' && (
                            <button
                              className="btn btn-success btn-sm"
                              onClick={() => approveDistribution(run.id)}
                            >
                              Approve
                            </button>
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
      </div>
    </div>
  );
};

export default DistributionGenerator;
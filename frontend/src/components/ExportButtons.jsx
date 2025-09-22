import React, { useState } from 'react';
import api from '../api';

const ExportButtons = () => {
  const [loading, setLoading] = useState(false);

  const handleExport = async (type) => {
    setLoading(true);
    try {
      const response = await api.get(`/admin/reports/donations?format=${type}`);

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `donations_report.${type}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      alert('Export failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container-fluid">
      <h2>Data Export</h2>

      <div className="row">
        <div className="col-md-6">
          <div className="card">
            <div className="card-header">
              <h5>Export Donations Report</h5>
            </div>
            <div className="card-body">
              <p>Download donation data in various formats</p>

              <div className="d-grid gap-2">
                <button
                  className="btn btn-success"
                  onClick={() => handleExport('csv')}
                  disabled={loading}
                >
                  {loading ? 'Exporting...' : 'Export as CSV'}
                </button>

                <button
                  className="btn btn-primary"
                  onClick={() => handleExport('xlsx')}
                  disabled={loading}
                >
                  {loading ? 'Exporting...' : 'Export as Excel'}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="col-md-6">
          <div className="card">
            <div className="card-header">
              <h5>Export Options</h5>
            </div>
            <div className="card-body">
              <ul className="list-unstyled">
                <li>✓ All donation records</li>
                <li>✓ Donor information (masked CNIC)</li>
                <li>✓ Transaction hashes for transparency</li>
                <li>✓ Date range filtering available</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExportButtons;
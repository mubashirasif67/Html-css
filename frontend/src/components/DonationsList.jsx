import React, { useState, useEffect } from 'react';
import api from '../api';

const DonationsList = () => {
  const [donations, setDonations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchDonations();
  }, []);

  const fetchDonations = async () => {
    try {
      const response = await api.get('/donations/all');
      setDonations(response.data);
    } catch (error) {
      setError('Failed to fetch donations');
      console.error('Error fetching donations:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString();
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
      <h2>Donations Management</h2>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="card">
        <div className="card-body">
          <div className="table-responsive">
            <table className="table table-striped">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Donor Name</th>
                  <th>Email</th>
                  <th>CNIC</th>
                  <th>Amount</th>
                  <th>Type</th>
                  <th>Date</th>
                  <th>Hash</th>
                </tr>
              </thead>
              <tbody>
                {donations.map((donation) => (
                  <tr key={donation.id}>
                    <td>{donation.id}</td>
                    <td>{donation.donor_name}</td>
                    <td>{donation.donor_email || 'N/A'}</td>
                    <td>{maskCNIC(donation.donor_cnic)}</td>
                    <td>Rs {donation.amount.toLocaleString()}</td>
                    <td>
                      <span className={`badge bg-${donation.donation_type === 'zakat' ? 'success' : donation.donation_type === 'sadaqah' ? 'warning' : 'info'}`}>
                        {donation.donation_type}
                      </span>
                    </td>
                    <td>{formatDate(donation.created_at)}</td>
                    <td>
                      <small className="text-muted">
                        {donation.transaction_hash ? donation.transaction_hash.substring(0, 8) + '...' : 'N/A'}
                      </small>
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

export default DonationsList;
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Line, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import api from '../services/api';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

function Dashboard({ user, onLogout }) {
  const [stats, setStats] = useState({
    donations: { total: 0, monthly: 0, total_amount: 0, monthly_amount: 0 },
    employees: { total: 0, eligible: 0, ineligible: 0 },
    distributions: { total: 0, pending: 0 },
    recent_donations: []
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      const response = await api.get('/admin/statistics/dashboard');
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const lineChartData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [{
      label: 'Monthly Donations',
      data: [12000, 19000, 15000, 25000, 22000, 30000],
      borderColor: 'rgb(75, 192, 192)',
      backgroundColor: 'rgba(75, 192, 192, 0.2)',
      tension: 0.1
    }]
  };

  const doughnutChartData = {
    labels: ['Zakat', 'Sadaqah', 'General'],
    datasets: [{
      data: [45, 30, 25],
      backgroundColor: [
        'rgba(255, 99, 132, 0.8)',
        'rgba(54, 162, 235, 0.8)',
        'rgba(255, 206, 86, 0.8)'
      ]
    }]
  };

  return (
    <div className="dashboard">
      {/* Navigation */}
      <nav className="navbar navbar-expand-lg navbar-dark bg-dark">
        <div className="container-fluid">
          <Link className="navbar-brand" to="/dashboard">
            <i className="fas fa-chart-line"></i> Admin Dashboard
          </Link>
          <div className="navbar-nav ms-auto">
            <span className="navbar-text me-3">
              Welcome, {user?.name || 'Admin'}
            </span>
            <button className="btn btn-outline-light btn-sm" onClick={onLogout}>
              <i className="fas fa-sign-out-alt"></i> Logout
            </button>
          </div>
        </div>
      </nav>

      <div className="container-fluid">
        <div className="row">
          {/* Sidebar */}
          <nav className="col-md-2 d-md-block bg-light sidebar py-3">
            <div className="position-sticky">
              <ul className="nav flex-column">
                <li className="nav-item">
                  <Link className="nav-link active" to="/dashboard">
                    <i className="fas fa-home"></i> Dashboard
                  </Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link" to="/donations">
                    <i className="fas fa-donate"></i> Donations
                  </Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link" to="/beneficiaries">
                    <i className="fas fa-users"></i> Beneficiaries
                  </Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link" to="/distribution">
                    <i className="fas fa-truck"></i> Distribution
                  </Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link" to="/reports">
                    <i className="fas fa-file-alt"></i> Reports
                  </Link>
                </li>
              </ul>
            </div>
          </nav>

          {/* Main Content */}
          <main className="col-md-10 ms-sm-auto px-md-4 py-3">
            <h1 className="h2 mb-4">Dashboard Overview</h1>

            {loading ? (
              <div className="text-center py-5">
                <div className="spinner-border text-primary" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
              </div>
            ) : (
              <>
                {/* Stats Cards */}
                <div className="row mb-4">
                  <div className="col-md-3 mb-3">
                    <div className="card text-white bg-primary">
                      <div className="card-body">
                        <h5 className="card-title">
                          <i className="fas fa-donate"></i> Total Donations
                        </h5>
                        <h2>{stats.donations.total}</h2>
                        <p className="mb-0">PKR {stats.donations.total_amount.toLocaleString()}</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="col-md-3 mb-3">
                    <div className="card text-white bg-success">
                      <div className="card-body">
                        <h5 className="card-title">
                          <i className="fas fa-calendar"></i> This Month
                        </h5>
                        <h2>{stats.donations.monthly}</h2>
                        <p className="mb-0">PKR {stats.donations.monthly_amount.toLocaleString()}</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="col-md-3 mb-3">
                    <div className="card text-white bg-info">
                      <div className="card-body">
                        <h5 className="card-title">
                          <i className="fas fa-users"></i> Beneficiaries
                        </h5>
                        <h2>{stats.employees.total}</h2>
                        <p className="mb-0">{stats.employees.eligible} eligible</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="col-md-3 mb-3">
                    <div className="card text-white bg-warning">
                      <div className="card-body">
                        <h5 className="card-title">
                          <i className="fas fa-truck"></i> Distributions
                        </h5>
                        <h2>{stats.distributions.total}</h2>
                        <p className="mb-0">{stats.distributions.pending} pending</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Charts */}
                <div className="row mb-4">
                  <div className="col-md-8">
                    <div className="card">
                      <div className="card-body">
                        <h5 className="card-title">Donation Trends</h5>
                        <Line data={lineChartData} />
                      </div>
                    </div>
                  </div>
                  
                  <div className="col-md-4">
                    <div className="card">
                      <div className="card-body">
                        <h5 className="card-title">Donation Types</h5>
                        <Doughnut data={doughnutChartData} />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Recent Donations Table */}
                <div className="card">
                  <div className="card-body">
                    <h5 className="card-title">Recent Donations</h5>
                    <div className="table-responsive">
                      <table className="table table-hover">
                        <thead>
                          <tr>
                            <th>ID</th>
                            <th>Donor</th>
                            <th>Amount</th>
                            <th>Type</th>
                            <th>Date</th>
                          </tr>
                        </thead>
                        <tbody>
                          {stats.recent_donations.map(donation => (
                            <tr key={donation.id}>
                              <td>#{donation.id}</td>
                              <td>{donation.donor}</td>
                              <td>PKR {donation.amount.toLocaleString()}</td>
                              <td>
                                <span className="badge bg-primary">{donation.type}</span>
                              </td>
                              <td>{new Date(donation.date).toLocaleDateString()}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
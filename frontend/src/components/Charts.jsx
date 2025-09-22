import React, { useState, useEffect } from 'react';
import api from '../api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';

const Charts = () => {
  const [summary, setSummary] = useState({});
  const [donationTrends, setDonationTrends] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      // Fetch dashboard summary
      const summaryResponse = await api.get('/admin/dashboard/summary');
      setSummary(summaryResponse.data);

      // Generate sample donation trends (since we don't have historical data endpoint)
      const trends = generateDonationTrends();
      setDonationTrends(trends);
    } catch (error) {
      console.error('Error fetching chart data:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateDonationTrends = () => {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return months.map((month, index) => ({
      month,
      donations: Math.floor(Math.random() * 500) + 100,
      amount: Math.floor(Math.random() * 500000) + 100000,
      beneficiaries: Math.floor(Math.random() * 200) + 50
    }));
  };

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

  if (loading) {
    return <div className="text-center"><div className="spinner-border"></div></div>;
  }

  return (
    <div className="container-fluid">
      <h2>Analytics Dashboard</h2>

      <div className="row">
        <div className="col-md-3">
          <div className="card text-center">
            <div className="card-body">
              <h5 className="card-title">Total Donations</h5>
              <h3 className="text-primary">{summary.total_donations}</h3>
            </div>
          </div>
        </div>

        <div className="col-md-3">
          <div className="card text-center">
            <div className="card-body">
              <h5 className="card-title">Total Amount</h5>
              <h3 className="text-success">Rs {summary.total_amount?.toLocaleString()}</h3>
            </div>
          </div>
        </div>

        <div className="col-md-3">
          <div className="card text-center">
            <div className="card-body">
              <h5 className="card-title">Total Employees</h5>
              <h3 className="text-info">{summary.total_employees}</h3>
            </div>
          </div>
        </div>

        <div className="col-md-3">
          <div className="card text-center">
            <div className="card-body">
              <h5 className="card-title">Eligible Employees</h5>
              <h3 className="text-warning">{summary.eligible_employees}</h3>
            </div>
          </div>
        </div>
      </div>

      <div className="row mt-4">
        <div className="col-md-8">
          <div className="card">
            <div className="card-header">
              <h5>Donation Trends</h5>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={donationTrends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="donations" stroke="#8884d8" name="Donations" />
                  <Line type="monotone" dataKey="amount" stroke="#82ca9d" name="Amount (Rs)" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="card">
            <div className="card-header">
              <h5>Distribution Status</h5>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Pending', value: summary.pending_distributions },
                      { name: 'Completed', value: summary.total_employees - summary.pending_distributions }
                    ]}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {[
                      { name: 'Pending', value: summary.pending_distributions },
                      { name: 'Completed', value: summary.total_employees - summary.pending_distributions }
                    ].map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      <div className="row mt-4">
        <div className="col-md-12">
          <div className="card">
            <div className="card-header">
              <h5>Monthly Overview</h5>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={donationTrends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="donations" fill="#8884d8" name="Donations" />
                  <Bar dataKey="beneficiaries" fill="#82ca9d" name="Beneficiaries" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Charts;
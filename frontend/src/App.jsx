import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './components/Login';
import DonationsList from './components/DonationsList';
import EmployeesList from './components/EmployeesList';
import DistributionGenerator from './components/DistributionGenerator';
import Charts from './components/Charts';
import ExportButtons from './components/ExportButtons';
import MLFlags from './components/MLFlags';
import './App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = React.useState(false);
  const [user, setUser] = React.useState(null);

  const handleLogin = (userData) => {
    setIsAuthenticated(true);
    setUser(userData);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setUser(null);
  };

  return (
    <Router>
      <div className="App">
        {isAuthenticated ? (
          <div className="admin-container">
            <nav className="navbar navbar-expand-lg navbar-dark bg-dark">
              <div className="container-fluid">
                <span className="navbar-brand">Blessings Admin Dashboard</span>
                <div className="navbar-nav ms-auto">
                  <span className="nav-link">Welcome, {user?.name}</span>
                  <button className="btn btn-outline-light" onClick={handleLogout}>Logout</button>
                </div>
              </div>
            </nav>

            <div className="container-fluid mt-4">
              <div className="row">
                <div className="col-md-2">
                  <div className="d-flex flex-column">
                    <a href="/dashboard/donations" className="btn btn-outline-primary mb-2">Donations</a>
                    <a href="/dashboard/employees" className="btn btn-outline-primary mb-2">Employees</a>
                    <a href="/dashboard/distribution" className="btn btn-outline-primary mb-2">Distribution</a>
                    <a href="/dashboard/charts" className="btn btn-outline-primary mb-2">Analytics</a>
                    <a href="/dashboard/ml-flags" className="btn btn-outline-primary mb-2">ML Flags</a>
                    <a href="/dashboard/export" className="btn btn-outline-primary mb-2">Export</a>
                  </div>
                </div>

                <div className="col-md-10">
                  <Routes>
                    <Route path="/dashboard/donations" element={<DonationsList />} />
                    <Route path="/dashboard/employees" element={<EmployeesList />} />
                    <Route path="/dashboard/distribution" element={<DistributionGenerator />} />
                    <Route path="/dashboard/charts" element={<Charts />} />
                    <Route path="/dashboard/ml-flags" element={<MLFlags />} />
                    <Route path="/dashboard/export" element={<ExportButtons />} />
                    <Route path="/" element={<Navigate to="/dashboard/donations" />} />
                  </Routes>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <Login onLogin={handleLogin} />
        )}
      </div>
    </Router>
  );
}

export default App;
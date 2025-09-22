import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import Login from './components/Login';
import Dashboard from './components/Dashboard';
import Donations from './components/Donations';
import Beneficiaries from './components/Beneficiaries';
import Distribution from './components/Distribution';
import Reports from './components/Reports';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Check if user is logged in
    const token = localStorage.getItem('access_token');
    const userData = localStorage.getItem('user');
    
    if (token && userData) {
      setIsAuthenticated(true);
      setUser(JSON.parse(userData));
    }
  }, []);

  const handleLogin = (userData, token) => {
    localStorage.setItem('access_token', token.access_token);
    localStorage.setItem('refresh_token', token.refresh_token);
    localStorage.setItem('user', JSON.stringify(userData));
    setIsAuthenticated(true);
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    setIsAuthenticated(false);
    setUser(null);
  };

  return (
    <Router>
      <div className="App">
        <ToastContainer position="top-right" autoClose={3000} />
        
        <Routes>
          <Route 
            path="/login" 
            element={
              isAuthenticated ? 
                <Navigate to="/dashboard" /> : 
                <Login onLogin={handleLogin} />
            } 
          />
          
          <Route
            path="/dashboard"
            element={
              isAuthenticated ?
                <Dashboard user={user} onLogout={handleLogout} /> :
                <Navigate to="/login" />
            }
          />
          
          <Route
            path="/donations"
            element={
              isAuthenticated ?
                <Donations user={user} onLogout={handleLogout} /> :
                <Navigate to="/login" />
            }
          />
          
          <Route
            path="/beneficiaries"
            element={
              isAuthenticated ?
                <Beneficiaries user={user} onLogout={handleLogout} /> :
                <Navigate to="/login" />
            }
          />
          
          <Route
            path="/distribution"
            element={
              isAuthenticated ?
                <Distribution user={user} onLogout={handleLogout} /> :
                <Navigate to="/login" />
            }
          />
          
          <Route
            path="/reports"
            element={
              isAuthenticated ?
                <Reports user={user} onLogout={handleLogout} /> :
                <Navigate to="/login" />
            }
          />
          
          <Route path="/" element={<Navigate to="/dashboard" />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
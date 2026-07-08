import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import '../styles/auth.css';

export const Signup = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    user_type: 'citizen',
    agency: '',
  });
  const [loading, setLoading] = useState(false);
  const { signup, error } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const success = await signup(
      formData.username,
      formData.email,
      formData.password,
      formData.user_type,
      formData.agency
    );
    setLoading(false);
    if (success) {
      navigate('/dashboard');
    }
  };

  return (
    <div className="hero-mini hero-mini--signup">
      <div className="container">
        <h1>Join CivicPulse</h1>
        <p className="lead">Create a free account to report issues and track government responses.</p>
      </div>

      <div className="container">
        <div className="row justify-content-center mb-5">
          <div className="col-md-6">
            <div className="card shadow form-card">
              <div className="card-header text-center">Sign Up</div>
              <div className="card-body p-4">
                {error && <div className="alert alert-danger">{error}</div>}

                <form onSubmit={handleSubmit}>
                  <div className="mb-3">
                    <label htmlFor="username" className="form-label">
                      Username
                    </label>
                    <input
                      type="text"
                      id="username"
                      className="form-control"
                      name="username"
                      value={formData.username}
                      onChange={handleChange}
                      required
                    />
                  </div>

                  <div className="mb-3">
                    <label htmlFor="email" className="form-label">
                      Email
                    </label>
                    <input
                      type="email"
                      id="email"
                      className="form-control"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      required
                    />
                  </div>

                  <div className="mb-3">
                    <label htmlFor="password" className="form-label">
                      Password
                    </label>
                    <input
                      type="password"
                      id="password"
                      className="form-control"
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      required
                      minLength="8"
                    />
                  </div>

                  <div className="mb-3">
                    <label htmlFor="user_type" className="form-label">
                      Account Type
                    </label>
                    <select
                      id="user_type"
                      className="form-control"
                      name="user_type"
                      value={formData.user_type}
                      onChange={handleChange}
                    >
                      <option value="citizen">Citizen</option>
                      <option value="govt">Government Officer</option>
                    </select>
                  </div>

                  {formData.user_type === 'govt' && (
                    <div className="mb-3">
                      <label htmlFor="agency" className="form-label">
                        Agency (Optional)
                      </label>
                      <input
                        type="text"
                        id="agency"
                        className="form-control"
                        name="agency"
                        value={formData.agency}
                        onChange={handleChange}
                      />
                    </div>
                  )}

                  <button
                    type="submit"
                    className="btn btn-primary w-100"
                    disabled={loading}
                  >
                    {loading ? 'Creating account...' : 'Create Account'}
                  </button>
                </form>

                <hr />
                <p className="text-center mb-0">
                  Already have an account? <Link to="/login">Log in</Link>
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Signup;

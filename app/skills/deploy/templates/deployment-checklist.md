# Deployment Checklist

## Pre-Deployment
- [ ] All tests passing on CI
- [ ] Code reviewed and approved
- [ ] No critical security vulnerabilities
- [ ] Database migrations tested
- [ ] Environment variables configured
- [ ] Rollback plan documented

## Deployment
- [ ] Notify team of deployment start
- [ ] Create deployment tag/release
- [ ] Run database migrations
- [ ] Deploy application
- [ ] Verify health checks pass
- [ ] Run smoke tests

## Post-Deployment
- [ ] Monitor error rates (15 min)
- [ ] Monitor response times (15 min)
- [ ] Verify key user flows work
- [ ] Check logs for unexpected errors
- [ ] Notify team of deployment completion
- [ ] Update deployment log

## Rollback Triggers
- Error rate > 5%
- P95 latency > 2x baseline
- Critical user flow broken
- Data integrity issues detected

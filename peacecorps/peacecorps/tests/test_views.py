import json
from urllib.parse import quote as urlquote

from django.core.urlresolvers import reverse
from django.test import Client, TestCase

from peacecorps.models import Account, Campaign, Country, FAQ, Media, Project


class DonationsTests(TestCase):
    fixtures = ['countries.yaml']

    def setUp(self):
        self.account = Account.objects.create(
            code='FUNDFUND', category=Account.PROJECT)
        self.project = Project.objects.create(
            slug='sluggy', country=Country.objects.get(name='Egypt'),
            account=self.account)

    def tearDown(self):
        self.project.delete()
        self.account.delete()

    def test_contribution_parameters(self):
        """ To get to the page where name, address are filled out before being
        shunted to pay.gov we need to pass the donation amount and project code
        as GET parameters. This makes sure they show up on the payment page.
        """

        response = self.client.get(
            '/donations/contribute/?amount=2000&project=' + self.account.code)
        content = response.content.decode('utf-8')
        self.assertEqual(200, response.status_code)
        self.assertTrue('$20.00' in content)
        self.assertTrue(self.account.code)     # Check that this is nonempty
        self.assertTrue(self.account.code in content)

    def test_payment_type(self):
        """Check that the payment type values are rendered correctly."""

        response = self.client.get(
            '/donations/contribute/?amount=2000&project=' + self.account.code)
        content = response.content.decode('utf-8')
        self.assertTrue('id_payment_type_0' in content)
        self.assertTrue('id_payment_type_1' in content)
        self.assertTrue('CreditCard' in content)
        self.assertTrue('CreditACH' in content)

    def test_review_page(self):
        """ Test that the donation review page renders with the required
        elements. """

        form_data = {
            'payer_name': 'William Williams',
            'billing_address':  '1 Main Street',
            'billing_city': 'Anytown',
            'billing_state': 'MD',
            'billing_zip':  '20852',
            'country': 'USA',
            'payment_amount': 2000,
            'project_code': 'PC-SEC01',
            'payment_type': 'CreditCard',
            'information_consent': 'true',
            'random': 'randVal'}

        response = self.client.post(
            '/donations/contribute/?amount=2000&project=' + self.account.code,
            form_data, HTTP_HOST='example.com')
        content = response.content.decode('utf-8')
        self.assertEqual(200, response.status_code)
        self.assertTrue('agency_tracking_id' in content)
        self.assertTrue('agency_id' in content)
        # this isn't a hidden value as it has the comma
        self.assertTrue('Anytown,' in content)
        self.assertTrue('name="random"' in content)
        self.assertTrue('value="randVal"' in content)

        #   Refetch the account so we can lookup its donorinfo
        account = Account.objects.get(pk=self.account.pk)
        self.assertEqual(1, len(account.donorinfos.all()))
        #   Also verify that the http host has been added
        donorinfo = account.donorinfos.get()
        self.assertTrue('://example.com' in donorinfo.xml)

    def test_review_page_not_appear(self):
        """The review page should *not* appear if a flag is provided"""
        form_data = {
            'payer_name': 'William Williams',
            'billing_address':  '1 Main Street',
            'billing_city': 'Anytown',
            'billing_state': 'MD',
            'billing_zip':  '20852',
            'country': 'USA',
            'payment_amount': 2000,
            'project_code': 'PC-SEC01',
            'payment_type': 'CreditCard',
            'information_consent': 'true'}

        response = self.client.post(
            reverse('donations_payment') + '?amount=2000&project='
            + self.account.code, form_data)
        self.assertContains(response, 'agency_tracking_id')
        form_data['force_form'] = 'true'
        response = self.client.post(
            reverse('donations_payment') + '?amount=2000&project='
            + self.account.code, form_data)
        self.assertNotContains(response, 'agency_tracking_id')

    def test_bad_request_donations(self):
        """ The donation information page should 400 if donation amount and
        project code aren't included. """
        response = self.client.get('/donations/contribute/')
        self.assertEqual(response.status_code, 400)

    def test_bad_amount(self):
        """ If a non-integer amount is entered, the donations/contribute page
        should 400. """

        response = self.client.get(
            '/donations/contribute/?amount=aaa&project_code=154')
        self.assertEqual(response.status_code, 400)

    def test_completed_success(self):
        response = self.client.get(reverse('donation success'))
        self.assertEqual(response.status_code, 200)


class DonatePagesTests(TestCase):

    fixtures = ['tests.yaml']

    # Do the pages load without error?
    def test_pages_rendering(self):
        response = self.client.get('/donate/')
        self.assertEqual(response.status_code, 200)

    def test_project_rendering(self):
        response = self.client.get('/donate/project/brick-oven-bakery/')
        self.assertEqual(response.status_code, 200)

    def test_fund_rendering(self):
        response = self.client.get(reverse(
            'donate campaign', kwargs={'slug': 'health-hivaids-fund'}))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('donate campaign',
                                           kwargs={'slug': 'cameroon'}))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse('donate campaign',
                    kwargs={'slug': 'stephanie-brown'}))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('donate campaign',
                                           kwargs={'slug': 'peace-corps'}))
        self.assertEqual(response.status_code, 200)

    def test_project_form_empty_amount(self):
        response = self.client.post('/donate/project/brick-oven-bakery/',
                                    {'presets': 'custom',
                                     'payment_amount': ''})
        self.assertEqual(response.status_code, 200)

    def test_project_form_low_amount(self):
        response = self.client.post('/donate/project/brick-oven-bakery/',
                                    {'presets': 'custom',
                                     'payment_amount': '0.99'})
        self.assertEqual(response.status_code, 200)

    def test_project_form_high_amount(self):
        response = self.client.post('/donate/project/brick-oven-bakery/',
                                    {'presets': 'custom',
                                     'payment_amount': '10000.00'})
        self.assertEqual(response.status_code, 200)

    def test_project_form_redirect_custom(self):
        """When selecting the fund-a-custom-amount option, everything should
        work"""
        response = self.client.post('/donate/project/brick-oven-bakery/',
                                    {'presets': 'custom',
                                     'payment_amount': '123.45'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue("12345" in response['Location'])
        code = Project.objects.get(slug='brick-oven-bakery').account.code
        self.assertTrue(code)
        self.assertTrue(code in response['Location'])

    def test_project_form_redirect_full(self):
        """If a project is funded, its overflow code should be used"""
        account = Account.objects.create(
            name='Full', code='FULL', goal=500, current=500,
            community_contribution=0)
        overflow = Account.objects.create(name='Overflow', code='OVERFLOW')
        project = Project.objects.create(
            country=Country.objects.get(name='China'), account=account,
            featured_image=Media.objects.get(pk=8), overflow=overflow,
            slug='proj-proj', published=True
        )

        response = self.client.post(
            reverse('donate project', kwargs={'slug': project.slug}),
            {'presets': 'preset-50'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue("5000" in response['Location'])
        self.assertTrue('OVERFLOW' in response['Location'])

        project.delete()
        overflow.delete()
        account.delete()

    def test_fund_form_redirect(self):
        """Campaign page should work as the project page does"""
        response = self.client.post(
            reverse('donate campaign', kwargs={'slug': 'peace-corps'}),
            {'presets': 'preset-50'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue("5000" in response['Location'])
        code = Campaign.objects.get(slug='peace-corps').account.code
        self.assertTrue(code)
        self.assertTrue(code in response['Location'])

    def test_project_success_failure(self):
        response = self.client.get(
            reverse('project success', kwargs={'slug': 'nonproj'}))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(
            reverse('project failure', kwargs={'slug': 'nonproj'}),
            follow=True)
        self.assertEqual(response.status_code, 404)
        response = self.client.get(
            reverse('project success',
                    kwargs={'slug': 'togo-clean-water-project'}))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('project failure',
                    kwargs={'slug': 'togo-clean-water-project'}), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_campaign_success_failure(self):
        response = self.client.get(
            reverse('campaign success', kwargs={'slug': 'nonproj'}))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(
            reverse('campaign failure', kwargs={'slug': 'nonproj'}),
            follow=True)
        self.assertEqual(response.status_code, 404)
        response = self.client.get(
            reverse('campaign success', kwargs={'slug': 'education-fund'}))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('campaign failure', kwargs={'slug': 'education-fund'}),
            follow=True)
        self.assertEqual(response.status_code, 200)

    def test_post_redirect(self):
        """All POSTs to the project/campaign success pages should get
        redirected to the same page as a GET"""
        for proj_camp, slug in (('project', 'togo-clean-water-project'),
                                ('campaign', 'education-fund')):
            url = reverse(proj_camp + ' success', kwargs={'slug': slug})
            for enforce_csrf_checks in (False, True):
                client = Client(enforce_csrf_checks=enforce_csrf_checks)
                response = client.post(
                    url, data={'agency_tracking_id': 'NEVERUSED'})
                self.assertEqual(response.status_code, 302)
                self.assertTrue(url in response['LOCATION'])
                response = client.post(
                    url + '?something=else',
                    data={'agency_tracking_id': 'NEVERUSED'})
                self.assertEqual(response.status_code, 302)
                self.assertTrue(url in response['LOCATION'])
                self.assertTrue('?something=else' in response['LOCATION'])

    def test_failure_redirect(self):
        """All POSTS to the project/campaign failure page should get
        redirected to a page with a big 'sorry' banner"""
        for proj_camp, slug in (('project', 'togo-clean-water-project'),
                                ('campaign', 'education-fund')):
            url = reverse(proj_camp + ' failure', kwargs={'slug': slug})
            for enforce_csrf_checks in (False, True):
                client = Client(enforce_csrf_checks=enforce_csrf_checks)
                response = client.post(
                    url, data={'agency_tracking_id': 'NEVERUSED'}, follow=True)
                self.assertContains(response, 'Unfortunately')
                response = client.post(
                    url + '?something=else',
                    data={'agency_tracking_id': 'NEVERUSED'}, follow=True)
                self.assertContains(response, 'Unfortunately')

    def test_memorial_fund_name(self):
        response = self.client.get(reverse('donate special funds'))
        self.assertNotContains(response, 'Stephanie Brown Memorial Fund</h3>')
        self.assertContains(response, 'Stephanie Brown')

    def test_success_render(self):
        """Verify that the donor's name and share links are present"""
        url = reverse('campaign success', kwargs={'slug': 'education-fund'})
        url += '?donor_name=Billy'
        response = self.client.get(url, HTTP_HOST='example.com')
        self.assertContains(response, 'Thank you, Billy')
        self.assertContains(response, urlquote('http://example.com/'))


class FAQTests(TestCase):
    def answer(self, value):
        return json.dumps({"data": [{
            "type": "text", "data": {"text": value}}]})

    def test_presence(self):
        FAQ.objects.create(question="Q1Q1Q1", answer=self.answer("A1A1A1"))
        FAQ.objects.create(question="Q2Q2Q2", answer=self.answer("A2A2A2"))
        FAQ.objects.create(question="Q3Q3Q3", answer=self.answer("A3A3A3"))
        response = self.client.get(reverse('donate faqs'))
        self.assertContains(response, 'Q1Q1Q1')
        self.assertContains(response, 'Q2Q2Q2')
        self.assertContains(response, 'Q3Q3Q3')
        self.assertContains(response, 'A1A1A1')
        self.assertContains(response, 'A2A2A2')
        self.assertContains(response, 'A3A3A3')
        FAQ.objects.all().delete()
